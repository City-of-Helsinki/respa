from helusers.admin import *
from respa_berth.models import berth_reservation, berth, sms_message, purchase


class BerthReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation',)

class BerthAdmin(admin.ModelAdmin):
    list_display = ('resource',)

class BerthPriceAdmin(admin.ModelAdmin):
    list_display = ('price',)

class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'success', 'to_phone_number')

class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_name', 'reserver_name', 'purchase_process_started', 'finished')

admin.site.register(berth_reservation.BerthReservation, BerthReservationAdmin)
admin.site.register(berth.Berth, BerthAdmin)
admin.site.register(berth.GroundBerthPrice, BerthPriceAdmin)
admin.site.register(sms_message.SMSMessage, SMSMessageAdmin)
admin.site.register(purchase.Purchase, PurchaseAdmin)