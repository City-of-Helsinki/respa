import datetime
from collections import OrderedDict

import pytz
import django.contrib.postgres.fields as pgfields
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils.dateformat import time_format
from django.utils.translation import ugettext_lazy as _
from psycopg2.extras import DateRange, NumericRange


STATE_BOOLS = {
    False: _('open'),
    True: _('closed'),
    None: _('-'),
}


def combine_datetime(date, time, tz):
    return tz.localize(datetime.datetime.combine(date, time))


def datetime_to_date(dt, tz):
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    else:
        dt = dt.astimezone(tz)
    return dt.date()


def get_opening_hours(time_zone, periods, begin, end=None):
    """
    Returns opening and closing times for a given date range

    Return value is a dict where keys are days on the range
        and values are a list of Day objects for that day's active period
        containing opening and closing hours

    :rtype : dict[str, list[dict[str, datetime.datetime]]]
    :type periods: list[Period]
    :type begin: datetime.date | datetime.datetime
    :type end: datetime.date | None
    """

    tz = pytz.timezone(time_zone)
    if begin is not None:
        if isinstance(begin, datetime.datetime):
            begin = datetime_to_date(begin, tz)
        assert isinstance(begin, datetime.date)

    if end is not None:
        if isinstance(end, datetime.datetime):
            end = datetime_to_date(end, tz)
        assert isinstance(end, datetime.date)

    if begin is None:
        begin = tz.localize(datetime.datetime.now()).date()
    if end is None:
        end = begin

    assert begin <= end

    periods = [p for p in periods if p.start <= end and p.end >= begin]
    # Periods are taken into account the highest priority first, then
    # the shortest length.
    for p in periods:
        if not hasattr(p, 'priority'):
            p.priority = 0
    periods.sort(key=lambda x: (-x.priority, x.end - x.start))

    days = list(Day.objects.filter(period__in=periods))
    for period in periods:
        period.range_days = {day.weekday: day for day in days if day.period_id == period.id}

    date = begin
    dates = OrderedDict()
    while date <= end:
        opens = None
        closes = None
        for period in periods:
            if period.start > date or period.end < date:
                continue
            # Currently the 'closed' field of periods do not
            # always contain sensible data. Ignore it for now.
            if False and period.closed:
                break
            day = period.range_days.get(date.weekday())
            if day is None or day.closed:
                break
            opens = combine_datetime(date, day.opens, tz)
            closes = combine_datetime(date, day.closes, tz)
            if opens == closes:
                # The interval is zero-length
                opens = None
                closes = None
            break

        dates[date] = [{'opens': opens, 'closes': closes}]
        date += datetime.timedelta(days=1)

    return dates


class Period(models.Model):
    """
    A period of time to express state of open or closed
    Days that specifies the actual activity hours link here
    """
    resource = models.ForeignKey('Resource', verbose_name=_('Resource'), db_index=True,
                                 null=True, blank=True, related_name='periods', on_delete=models.CASCADE)
    unit = models.ForeignKey('Unit', verbose_name=_('Unit'), db_index=True,
                             null=True, blank=True, related_name='periods', on_delete=models.CASCADE)

    start = models.DateField(verbose_name=_('Start date'))
    end = models.DateField(verbose_name=_('End date'))

    name = models.CharField(max_length=200, verbose_name=_('Name'), blank=True, default='')
    description = models.CharField(verbose_name=_('Description'), null=True,
                                   blank=True, max_length=500)
    closed = models.BooleanField(verbose_name=_('Closed'), default=False, editable=False)

    class Meta:
        verbose_name = _("period")
        verbose_name_plural = _("periods")

    def __str__(self):
        # FIXME: output date in locale-specific format
        return "{0}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}".format(self.name, self.start, self.end, STATE_BOOLS[self.closed])

    def _validate_belonging(self):
        if not (self.resource_id or self.unit_id):
            raise ValidationError(_("You must set 'resource' or 'unit'"), code="no_belonging")

        if self.resource_id and self.unit_id:
            raise ValidationError(_("You must set either 'resource' or 'unit', but not both"), code="invalid_belonging")

    def _check_closed(self):
        # TODO: why is this automagically closing itself upon creation when there's no days added yet
        if self.pk:
            # The period is not `closed` if it has any `open` days
            self.closed = not self.days.filter(closed=False).exists()
        else:  # Unsaved period, thus has no days, thus is closed.
            self.closed = True

    def clean(self, ignore_overlap=False):
        super(Period, self).clean()

        if self.start is None or self.end is None:
            raise ValidationError(_("You must set 'start' and 'end' fields."), code="empty_start_end")

        if self.start > self.end:
            raise ValidationError("Period must start before its end", code="invalid_date_range")

        self._check_closed()

    def save(self, *args, **kwargs):
        ignore_overlap = kwargs.pop('ignore_overlap', False)
        self._validate_belonging()
        self.clean(ignore_overlap=ignore_overlap)
        self.duration = DateRange(self.start, self.end, '[]')
        return super(Period, self).save(*args, **kwargs)

    def save_closedness(self):
        """
        Recalculate and save the `closed`ness state for the day.
        """
        self._check_closed()
        self.save(force_update=True, update_fields=("closed",))


class Day(models.Model):
    """
    Day of week and its active start and end time and whether it is open or closed

    Kirjastot.fi API uses closed for both days and periods, don't know which takes precedence
    """
    DAYS_OF_WEEK = (
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday'))
    )

    period = models.ForeignKey(Period, verbose_name=_('Period'), db_index=True, related_name='days',
                               on_delete=models.CASCADE)
    weekday = models.IntegerField(verbose_name=_('Weekday'), choices=DAYS_OF_WEEK)
    opens = models.TimeField(verbose_name=_('Time when opens'), null=True, blank=True)
    closes = models.TimeField(verbose_name=_('Time when closes'), null=True, blank=True)
    length = pgfields.IntegerRangeField(verbose_name=_('Range between opens and closes'), null=True,
                                        blank=True, db_index=True)
    # NOTE: If this is true and the period is false, what then?
    closed = models.NullBooleanField(verbose_name=_('Closed'), default=False)
    description = models.CharField(max_length=200, verbose_name=_('description'), null=True, blank=True)

    class Meta:
        verbose_name = _("day")
        verbose_name_plural = _("days")

    def __str__(self):
        # FIXME: output date in locale-specific format
        if self.opens and self.closes:
            hours = ", {0} - {1}".format(time_format(self.opens, "G:i"), time_format(self.closes, "G:i"))
        else:
            hours = ""
        return "{4}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}, {0}: {3} {5}".format(
            self.get_weekday_display(), self.period.start, self.period.end,
            STATE_BOOLS[self.closed], self.period.name, hours)

    def save(self, *args, **kwargs):
        if self.opens and self.closes:
            try:
                opens = int(self.opens.isoformat().replace(":", ""))
                closes = int(self.closes.isoformat().replace(":", ""))
            except AttributeError:
                opens = int(self.opens.replace(":", ""))
                closes = int(self.closes.replace(":", ""))
            self.length = NumericRange(opens, closes)
        return super(Day, self).save(*args, **kwargs)
