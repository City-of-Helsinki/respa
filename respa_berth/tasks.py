
# -*- coding: utf-8 -*-

from datetime import timedelta
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from respa import celery_app as app
from django.contrib.auth.models import AnonymousUser
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from respa_berth.sms import send_sms
from django.conf import settings
from django.db.models import Q
import hashlib
import time

@app.task
def retry_sms():
    from respa_berth.models.sms_message import SMSMessage
    from resources.models.reservation import Reservation
    two_days_ago = timezone.now() - timedelta(days=2)
    hour_ago = timezone.now() - timedelta(hours=1)
    sms_messages = SMSMessage.objects.filter(berth_reservation__reservation__state=Reservation.CONFIRMED, success=False, created_at__gte=two_days_ago, created_at__lte=hour_ago)

    for sms_message in sms_messages:
        send_sms(sms_message.to_phone_number, sms_message.message_body, sms_message.berth_reservation, sms_message)
        time.sleep(1)


@app.task
def check_reservability():
    from respa_berth.models.berth_reservation import BerthReservation
    from resources.models.reservation import Reservation
    from respa_berth.models.berth import Berth
    unavailable_berths = Berth.objects.filter(resource__reservable=False, is_deleted=False).exclude(type__in=[Berth.GROUND])

    for berth in unavailable_berths:
        if berth.type == Berth.DOCK and berth.berth_reservations.filter(reservation__state=Reservation.CONFIRMED, key_returned=False).exists():
            continue
        if not BerthReservation.objects.filter(berth=berth, reservation__end__gte=timezone.now(), reservation__state=Reservation.CONFIRMED).exists():
            resource = berth.resource
            resource.reservable = True
            resource.save()

    reservations = BerthReservation.objects.filter(reservation__end__gte=timezone.now(), reservation__state=Reservation.CONFIRMED)
    berths = Berth.objects.filter(berth_reservations__in=reservations, resource__reservable=True)
    for berth in berths:
        resource = berth.resource
        resource.reservable = False
        resource.save()

    Berth.objects.exclude(berth_reservations__in=reservations).filter(is_disabled=False, type=Berth.GROUND).update(is_disabled=True)

@app.task
def cancel_failed_reservation(purchase_id):
    from respa_berth.models.purchase import Purchase
    from respa_berth.models.berth import Berth
    purchase = Purchase.objects.get(pk=purchase_id)
    if not purchase.is_success() and not purchase.is_finished():
        user = AnonymousUser()
        purchase.berth_reservation.cancel_reservation(user)
        purchase.set_finished()
        berth = purchase.berth_reservation.berth
        if berth.type == Berth.GROUND and not berth.is_disabled:
            berth.is_disabled = True
            berth.save()

@app.task
def cancel_failed_reservations():
    from respa_berth.models.purchase import Purchase
    from respa_berth.models.berth import Berth
    three_days_ago = timezone.now() - timedelta(days=3)
    failed_purchases = Purchase.objects.filter(created_at__lte=three_days_ago, purchase_process_notified__isnull=True, finished__isnull=True, berth_reservation__is_paid=False)
    user = AnonymousUser()
    for purchase in failed_purchases:
        purchase.berth_reservation.cancel_reservation(user)
        purchase.set_finished()
        if purchase.berth_reservation.reservation.reserver_email_address:
            send_cancel_email(purchase.berth_reservation)
        if purchase.berth_reservation.reservation.reserver_phone_number:
            send_cancel_sms(purchase.berth_reservation)
        berth = purchase.berth_reservation.berth
        if berth.type == Berth.GROUND and not berth.is_disabled:
            berth.is_disabled = True
            berth.save()
        time.sleep(1)

@app.task
def check_key_returned():
    from respa_berth.models.berth_reservation import BerthReservation
    from respa_berth.models.berth import Berth
    from resources.models.reservation import Reservation
    now_minus_week = timezone.now() - timedelta(weeks=1)
    reservations = BerthReservation.objects.filter(Q(key_return_notification_sent_at__lte=now_minus_week) | Q(key_return_notification_sent_at=None), berth__type=Berth.DOCK, reservation__end__lte=timezone.now(), key_returned=False, reservation__state=Reservation.CONFIRMED).exclude(child__reservation__state=Reservation.CONFIRMED).distinct()

    for reservation in reservations:
        sent = False
        if reservation.reservation.reserver_email_address:
            sent = True
            send_key_email(reservation)
        if reservation.reservation.reserver_phone_number:
            sent = True
            send_key_sms(reservation)
        if sent:
            reservation.key_return_notification_sent_at = timezone.now()
            reservation.save()
            time.sleep(1)


@app.task
def check_ended_reservations():
    from respa_berth.models.berth_reservation import BerthReservation
    from respa_berth.models.berth import Berth
    from resources.models.reservation import Reservation
    now_minus_day = timezone.now() - timedelta(hours=24)
    reservations = BerthReservation.objects.filter(reservation__state=Reservation.CONFIRMED, reservation__end__range=(now_minus_day, timezone.now())).exclude(child__reservation__state=Reservation.CONFIRMED).distinct()

    for reservation in reservations:
        berth = reservation.berth
        if berth.type == Berth.GROUND:
            berth.is_disabled = True
            berth.save()
        sent = False
        if reservation.end_notification_sent_at:
            continue
        if reservation.reservation.reserver_email_address:
            sent = True
            send_end_email(reservation)
        if reservation.reservation.reserver_phone_number:
            sent = True
            send_end_sms(reservation)
        if sent:
            reservation.end_notification_sent_at = timezone.now()
            reservation.save()
            time.sleep(1)

#This task is run manually once after initial deployment
@app.task
def send_initial_renewal_notification(reservation_id):
    from respa_berth.models.berth_reservation import BerthReservation
    reservation = BerthReservation.objects.get(pk=reservation_id)
    if not reservation.renewal_code:
        reservation.set_renewal_code()
    if reservation.reservation.reserver_email_address:
        send_renewal_email(reservation)
    if reservation.reservation.reserver_phone_number:
        send_renewal_sms(reservation)

@app.task
def check_and_handle_reservation_renewals():
    from respa_berth.models.berth_reservation import BerthReservation
    from resources.models.reservation import Reservation
    now_plus_month = timezone.now() + timedelta(days=30)
    now_plus_week = timezone.now() + timedelta(days=7)
    now_plus_day = timezone.now() + timedelta(days=1)
    reservations = BerthReservation.objects.filter(reservation__end__lte=now_plus_month, reservation__end__gte=timezone.now(), reservation__state=Reservation.CONFIRMED).exclude(child__reservation__state=Reservation.CONFIRMED).distinct()

    for reservation in reservations:
        sent = False
        if reservation.reservation.end < now_plus_day:
            if reservation.renewal_notification_day_sent_at:
                continue
            if not reservation.renewal_code:
                reservation.set_renewal_code()
            if reservation.reservation.reserver_email_address:
                sent = True
                send_renewal_email(reservation, 'day')
            if reservation.reservation.reserver_phone_number:
                sent = True
                send_renewal_sms(reservation)
            if sent:
                reservation.renewal_notification_day_sent_at = timezone.now()
                reservation.save()
                time.sleep(1)

        elif reservation.reservation.end < now_plus_week:
            if reservation.renewal_notification_week_sent_at:
                continue
            if not reservation.renewal_code:
                reservation.set_renewal_code()
            if reservation.reservation.reserver_email_address:
                sent = True
                send_renewal_email(reservation, 'week')
            if reservation.reservation.reserver_phone_number:
                sent = True
                send_renewal_sms(reservation)
            if sent:
                reservation.renewal_notification_week_sent_at = timezone.now()
                reservation.save()
                time.sleep(1)
        else:
            if reservation.renewal_notification_month_sent_at:
                continue
            if not reservation.renewal_code:
                reservation.set_renewal_code()
            if reservation.reservation.reserver_email_address:
                sent = True
                send_renewal_email(reservation, 'month')
            if reservation.reservation.reserver_phone_number:
                sent = True
                send_renewal_sms(reservation)
            if sent:
                reservation.renewal_notification_month_sent_at = timezone.now()
                reservation.save()
                time.sleep(1)

@app.task
def send_confirmation(reservation_id):
    from respa_berth.models.berth_reservation import BerthReservation
    reservation = BerthReservation.objects.get(pk=reservation_id)
    if reservation.reservation.reserver_email_address:
        send_confirmation_email(reservation)
    if reservation.reservation.reserver_phone_number:
        send_confirmation_sms(reservation)


def send_renewal_email(reservation, notification_type=None):
    full_name = reservation.reservation.reserver_name
    recipients = [reservation.reservation.reserver_email_address]
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    code = reservation.renewal_code
    renewal_link = 'https://varaukset.hameenlinna.fi/#renewal/' + code
    if settings.DEBUG:
        renewal_link = 'https://varaukset.haltudemo.fi/#renewal/' + code

    #body_html = _('<h2>Greetings %(full_name)s,</h2><br><br>Your berth reservation will end %(end_date_finnish)s. You can renew your reservation from the link eblow. If you don\'t renew your reservation before it ends the berth will be unlocked for everyone to reserve.<br><br>Renew your berth reservation <a href="%(renewal_link)s"> here</a>') % {'full_name': full_name, 'end_date_finnish': end_date_finnish, 'renewal_link': renewal_link}
    #body_plain = _('Greetings %(full_name)s\n\nYour berth reservation will end %(end_date_finnish)s. You can renew your reservation from the link below. If you don\'t renew your reservation before it ends the berth will be unlocked for everyone to reserve. \n\nRenew your berth reservation here: %(renewal_link)s') % {'full_name': full_name, 'end_date_finnish': end_date_finnish, 'renewal_link': renewal_link}

    #if notification_type == 'month':
    #    topic = _('Your berth reservation will end in a month. Renew your reservation now!')
    #elif notification_type == 'week':
    #    topic = _('Your berth reservation will end in a week. Renew your reservation now!')
    #else:
    #    topic = _('Your berth reservation will end. Renew your reservation now!')

    topic = 'Venepaikkavarauksesi päättyy. Uusi varauksesi nyt!'

    if notification_type == 'month':
        topic = 'Venepaikkavarauksesi päättyy kuukauden päästä. Uusi varauksesi nyt!'
    elif notification_type == 'week':
        topic = 'Venepaikkavarauksesi päättyy viikon päästä. Uusi varauksesi nyt!'
    elif notification_type == 'day':
        topic = 'Venepaikkavarauksesi päättyy tänään. Uusi varauksesi nyt!'


    body_plain = '''Hei {0},\n\n
Venepaikkavarauksesi päättyy {1}.
Voit uusia venepaikkavarauksesi alla olevasta linkistä tai asioimalla sellaisessa palvelupisteessä, josta löytyy kassapalvelut.
Palvelupisteiden yhteystiedot löydät osoitteesta www.hameenlinna.fi/Asiointi/Palvelupisteet/.
Mikäli et uusi varaustasi ennen sen päättymistä, venepaikka vapautuu järjestelmään avoimesti varattavaksi.\n\n
Linkki on käytettävissä n. 20min päästä uudelleen, mikäli venepaikan uusinta epäonnistuu (ei mene kokonaisuudessaan läpi). Uusi varauksesi osoitteesta: {2}'''.format(full_name, end_date_finnish, renewal_link)

    body_html = '''<p>Hei {0},</p>
    <p>Venepaikkavarauksesi päättyy {1}.
    Voit uusia venepaikkavarauksesi alla olevasta linkistä tai asioimalla sellaisessa palvelupisteessä, josta löytyy kassapalvelut.
    Palvelupisteiden yhteystiedot löydät osoitteesta www.hameenlinna.fi/Asiointi/Palvelupisteet/.
    Mikäli et uusi varaustasi ennen sen päättymistä, venepaikka vapautuu järjestelmään avoimesti varattavaksi.</p>
    <p>Uusi venepaikkavarauksesi <a href="{2}">tästä</a>.</p> <p>Linkki on käytettävissä n. 20min päästä uudelleen, mikäli venepaikan uusinta epäonnistuu (ei mene kokonaisuudessaan läpi).</p>'''.format(full_name, end_date_finnish, renewal_link)

    send_mail(
        topic,
        body_plain,
        settings.EMAIL_FROM,
        recipients,
        html_message=body_html,
        fail_silently=False,
    )


def send_renewal_sms(reservation):
    full_name = reservation.reservation.reserver_name
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    code = reservation.renewal_code
    renewal_link = 'https://varaukset.hameenlinna.fi/#renewal/' + code
    if settings.DEBUG:
        renewal_link = 'https://varaukset.haltudemo.fi/#renewal/' + code
    phone_number = str(reservation.reservation.reserver_phone_number)
    if phone_number[0] == '0':
        phone_number = '+358' + phone_number[1:]
    body_plain = 'Hei, venepaikkavarauksesi päättyy {0}. Uusi se palvelupisteessä tai: {1}'.format(end_date_finnish, renewal_link)
    send_sms(phone_number, body_plain, reservation)


def send_end_email(reservation):
    full_name = reservation.reservation.reserver_name
    recipients = [reservation.reservation.reserver_email_address]
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)

    topic = 'Venepaikkavarauksesi on päättynyt'

    body_plain = '''Hei {0},\n\n
Venepaikkavarauksesi on päättynyt {1}.
Venepaikka on nyt vapaasti kaikkien varattavissa. Kiitos varauksestasi!
Jos venepaikkasi oli lukitulla venelaiturilla, muista palauttaa laiturin avain viikon kuluessa varauksen päättymisestä.
Poletit mitätöityvät automaattisesti eikä niitä tarvitse palauttaa.'''.format(full_name, end_date_finnish)

    body_html = '''<p>Hei {0},</p>
    <p>Venepaikkavarauksesi on päättynyt {1}.
    Venepaikka on nyt vapaasti kaikkien varattavissa. Kiitos varauksestasi!
    Jos venepaikkasi oli lukitulla venelaiturilla, muista palauttaa laiturin avain viikon kuluessa varauksen päättymisestä.
    Poletit mitätöityvät automaattisesti eikä niitä tarvitse palauttaa.</p>'''.format(full_name, end_date_finnish)


    send_mail(
        topic,
        body_plain,
        settings.EMAIL_FROM,
        recipients,
        html_message=body_html,
        fail_silently=False,
    )


def send_end_sms(reservation):
    full_name = reservation.reservation.reserver_name
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    phone_number = str(reservation.reservation.reserver_phone_number)
    if phone_number[0] == '0':
        phone_number = '+358' + phone_number[1:]
    body_plain = 'Hei, venepaikkavarauksesi on päättynyt {0}. Venepaikka on nyt kaikkien varattavissa.'.format(end_date_finnish)
    if reservation.berth.type == 'dock':
        body_plain += ' Muista palauttaa venepaikan avain.'

    body_plain += ' Terveisin Hämeenlinnan kaupunki.'
    send_sms(phone_number, body_plain, reservation)


def send_key_email(reservation):
    full_name = reservation.reservation.reserver_name
    recipients = [reservation.reservation.reserver_email_address]
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)

    #body_html = _('<h2>Greetings %(full_name)s,</h2><br><br>Your berth reservation has ended %(end_date_finnish)s but you haven\'t returned the key. Please return the key as soon as possible!') % {'full_name': full_name, 'end_date_finnish': end_date_finnish}
    #body_plain = _('Greetings %(full_name)s\n\nYour berth reservation has ended %(end_date_finnish)s but you haven\'t returned the key. Please return the key as soon as possible!') % {'full_name': full_name, 'end_date_finnish': end_date_finnish}
    #topic = _('You haven\'t returned the key of your berth reservation. Please return the key!')

    topic = 'Et ole vielä palauttanut varaamasi venelaituripaikan avainta!'

    body_plain = '''Hei {0},\n\n
Venepaikkavarauksesi on päättynyt {1}.
Venelaiturin avain tulee palauttaa viikon kuluessa varauksen päättymisestä.
Palauttamattomasta avaimesta peritään hinnaston mukainen maksu.'''.format(full_name, end_date_finnish)

    body_html = '''<p>Hei {0},</p>
    <p>Venepaikkavarauksesi on päättynyt {1}.
    Venelaiturin avain tulee palauttaa viikon kuluessa varauksen päättymisestä.
    Palauttamattomasta avaimesta peritään hinnaston mukainen maksu.</p>'''.format(full_name, end_date_finnish)

    send_mail(
        topic,
        body_plain,
        settings.EMAIL_FROM,
        recipients,
        html_message=body_html,
        fail_silently=False,
    )


def send_key_sms(reservation):
    full_name = reservation.reservation.reserver_name
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    phone_number = str(reservation.reservation.reserver_phone_number)
    if phone_number[0] == '0':
        phone_number = '+358' + phone_number[1:]
    body_plain = 'Hei, venepaikkavarauksesi on päättynyt {0}. Palauta avain viikon kuluessa tai perimme hinnaston mukaisen maksun. Terveisin Hämeenlinnan kaupunki.'.format(end_date_finnish)
    send_sms(phone_number, body_plain, reservation)


def send_confirmation_email(reservation):
    full_name = reservation.reservation.reserver_name
    recipients = [reservation.reservation.reserver_email_address]
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    begin_date = reservation.reservation.begin
    begin_date_finnish = str(begin_date.day) + '.' + str(begin_date.month) + '.' + str(begin_date.year)
    berth_name = reservation.berth.get_name_and_unit()

    #body_html = _('<h2>Greetings %(full_name)s,</h2><br><br>Thank you for your berth reservation! Here is a summary of your reservation: <br><br>Begin:%(begin_date_finnish)s <br>End: %(end_date_finnish)s <br>Berth: %(berth_name)s') % {'full_name': full_name, 'begin_date_finnish': begin_date_finnish, 'end_date_finnish': end_date_finnish, 'berth_name': berth_name}
    #body_plain = _('Greetings %(full_name)s\n\nThank you for your berth reservation! Here is a summary of your reservation: \n\nBegin:%(begin_date_finnish)s \nEnd: %(end_date_finnish)s \nBerth: %(berth_name)s') % {'full_name': full_name, 'begin_date_finnish': begin_date_finnish, 'end_date_finnish': end_date_finnish, 'berth_name': berth_name}
    #topic = _('A confirmation of your berth reservation')

    topic = 'Vahvistus venepaikkavarauksestasi'

    body_plain = '''Hei {0},\n\n
Kiitos venepaikkavarauksestasi! Tässä yhteenveto varauksestasi:\n
Alkupäivä: {1}\n
Loppupäivä: {2}\n
Venepaikka: {3}\n\n
Lukittujen laituripaikkojen avaimet ja maallevetoalueiden poletit noudetaan palvelupiste Kastellista. Uusiessasi olemassa olevan varauksen et tarvitse uutta polettia.
Palvelupisteiden yhteystiedot löydät osoitteesta https://www.hameenlinna.fi/hallinto-ja-talous/neuvonta-ja-asiointi/kirjasto-palvelupisteet/.
Hakiessasi avainta tai polettia varauduthan todistamaan henkilöllisyytesi.
Lisää venerantojen sekä laituripaikkojen käytöstä osoitteessa https://www.hameenlinna.fi/vesireititjaveneily.
'''.format(full_name, begin_date_finnish, end_date_finnish, berth_name)

    body_html = '''<p>Hei {0},</p>
    <p>Kiitos venepaikkavarauksestasi! Tässä yhteenveto varauksestasi:</p>
    <p><strong>Alkupäivä</strong>: {1}</p>
    <p><strong>Loppupäivä</strong>: {2}</p>
    <p><strong>Venepaikka</strong>: {3}</p>
    <p>Lukittujen laituripaikkojen avaimet ja maallevetoalueiden poletit noudetaan palvelupiste Kastellista. Uusiessasi olemassa olevan varauksen et tarvitse uutta polettia.
    Palvelupisteiden yhteystiedot löydät osoitteesta https://www.hameenlinna.fi/hallinto-ja-talous/neuvonta-ja-asiointi/kirjasto-palvelupisteet/.
    Hakiessasi avainta tai polettia varauduthan todistamaan henkilöllisyytesi.
    Lisää venerantojen sekä laituripaikkojen käytöstä osoitteessa https://www.hameenlinna.fi/vesireititjaveneily.</p>'''.format(full_name, begin_date_finnish, end_date_finnish, berth_name)

    send_mail(
        topic,
        body_plain,
        settings.EMAIL_FROM,
        recipients,
        html_message=body_html,
        fail_silently=False,
    )


def send_confirmation_sms(reservation):
    full_name = reservation.reservation.reserver_name
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    begin_date = reservation.reservation.begin
    begin_date_finnish = str(begin_date.day) + '.' + str(begin_date.month) + '.' + str(begin_date.year)
    berth_name = reservation.berth.get_name_and_unit()
    phone_number = str(reservation.reservation.reserver_phone_number)
    if phone_number[0] == '0':
        phone_number = '+358' + phone_number[1:]
    body_plain = 'Varauksesi on vahvistettu aikavälille {0} - {1}. Venepaikka: {2}. Laituripaikkojen avaimet ja maallevetoalueiden poletit noudetaan palvelupiste Kastellista. Terveisin Hämeenlinnan kaupunki.'.format(begin_date_finnish, end_date_finnish, berth_name)
    send_sms(phone_number, body_plain, reservation)


def send_cancel_email(reservation):
    full_name = reservation.reservation.reserver_name
    recipients = [reservation.reservation.reserver_email_address]
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    begin_date = reservation.reservation.begin
    begin_date_finnish = str(begin_date.day) + '.' + str(begin_date.month) + '.' + str(begin_date.year)
    berth_name = reservation.berth.get_name_and_unit()

    #body_html = _('<h2>Greetings %(full_name)s,</h2><br><br>Your berth reservation has been cancelled due to problems in payment process! Here is a summary of the cancelled reservation: <br><br>Begin:%(begin_date_finnish)s <br>End: %(end_date_finnish)s <br>Berth: %(berth_name)s') % {'full_name': full_name, 'begin_date_finnish': begin_date_finnish, 'end_date_finnish': end_date_finnish, 'berth_name': berth_name}
    #body_plain = _('Greetings %(full_name)s\n\nYour berth reservation has been cancelled due to problems in payment process! Here is a summary of the cancelled reservation: \n\nBegin:%(begin_date_finnish)s \nEnd: %(end_date_finnish)s \nBerth: %(berth_name)s') % {'full_name': full_name, 'begin_date_finnish': begin_date_finnish, 'end_date_finnish': end_date_finnish, 'berth_name': berth_name}
    #topic = _('Your berth reservation has been cancelled')

    topic = 'Vahvistus venepaikkavarauksestasi'

    body_plain = '''Hei {0},\n\n
Venepaikkavarauksesi on peruutettu maksupalvelujärjestelmän teknisen häiriön vuoksi!
Tässä yhteenveto peruutetusta varauksesta:\n
Alkupäivä: {1}\n
Loppupäivä: {2}\n
Venepaikka: {3}\n\n
Pahoittelemme järjestelmässä tapahtunutta häiriöitä.
Jos venepaikan varaaminen ei onnistu järjestelmän kautta, voit tehdä varauksen sellaisessa palvelupisteessä, josta löytyy kassapalvelut.
Palvelupisteiden yhteystiedot löydät osoitteesta http://www.hameenlinna.fi/Asiointi/Palvelupisteet/.'''.format(full_name, begin_date_finnish, end_date_finnish, berth_name)

    body_html = '''<p>Hei {0},</p>
    <p>Venepaikkavarauksesi on peruutettu maksupalvelujärjestelmän teknisen häiriön vuoksi! Tässä yhteenveto peruutetusta varauksesta:</p>
    <p><strong>Alkupäivä</strong>: {1}</p>
    <p><strong>Loppupäivä</strong>: {2}</p>
    <p><strong>Venepaikka</strong>: {3}</p>
    <p>Pahoittelemme järjestelmässä tapahtunutta häiriöitä.
    Jos venepaikan varaaminen ei onnistu järjestelmän kautta, voit tehdä varauksen sellaisessa palvelupisteessä, josta löytyy kassapalvelut.
    Palvelupisteiden yhteystiedot löydät osoitteesta http://www.hameenlinna.fi/Asiointi/Palvelupisteet/.</p>'''.format(full_name, begin_date_finnish, end_date_finnish, berth_name)

    send_mail(
        topic,
        body_plain,
        settings.EMAIL_FROM,
        recipients,
        html_message=body_html,
        fail_silently=False,
    )


def send_cancel_sms(reservation):
    full_name = reservation.reservation.reserver_name
    end_date = reservation.reservation.end
    end_date_finnish = str(end_date.day) + '.' + str(end_date.month) + '.' + str(end_date.year)
    begin_date = reservation.reservation.begin
    begin_date_finnish = str(begin_date.day) + '.' + str(begin_date.month) + '.' + str(begin_date.year)
    berth_name = reservation.berth.get_name_and_unit()
    phone_number = str(reservation.reservation.reserver_phone_number)
    if phone_number[0] == '0':
        phone_number = '+358' + phone_number[1:]
    body_plain = 'Hei, venepaikkavarauksesi epäonnistui. Yritit varausta aikavälille {0} - {1}, venepaikkaan {2}. Ota yhteys palvelupisteeseen. Terveisin Hämeenlinnan kaupunki.'.format(begin_date_finnish, end_date_finnish, berth_name)
    send_sms(phone_number, body_plain, reservation)
