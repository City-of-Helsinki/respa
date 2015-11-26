import datetime

import arrow
import django.contrib.postgres.fields as pgfields
import django.db.models as dbm
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils.dateformat import time_format
from django.utils.translation import ugettext_lazy as _
from psycopg2.extras import DateRange, NumericRange

from .utils import time_to_dtz

STATE_BOOLS = {False: _('open'), True: _('closed')}


def get_opening_hours(periods, begin, end=None):
    """
    Returns opening and closing times for a given date range

    Return value is a dict where keys are days on the range
        and values are a list of Day objects for that day's active period
        containing opening and closing hours

    :rtype : dict[str, list[dict[str, datetime.datetime]]]
    :type periods: list[Period]
    :type begin: datetime.date
    :type end: datetime.date | None
    """

    periods = periods.filter(start__lte=begin, end__gte=end).order_by('start', 'end')
    days = Day.objects.filter(period__in=periods)

    for period in periods:
        period.range_days = [day for day in days if day.period == period]

    periods = {per: [exper for exper in periods if exper.exception and exper.parent == per]
               for per in periods if not per.exception}

    begin_dt = datetime.datetime.combine(begin, datetime.time(0, 0))
    if end:
        end_dt = datetime.datetime.combine(end, datetime.time(0, 0))
    else:
        end_dt = begin_dt

    assert begin_dt <= end_dt

    # Generates a dict of time range's days as keys and values as active period's days
    dates = {}
    for period, exception_periods in periods.items():

        # Date range for periods needs to be given start and end days, but other periods get to keep their range
        if period.start < begin_dt.date():
            start = begin_dt
        else:
            start = arrow.get(period.start)
        if period.end > end_dt.date():
            end = end_dt
        else:
            end = arrow.get(period.end)

        # For one period, generate all of its days and for given day, put its hours into the dict
        for r in arrow.Arrow.range('day', start, end):
            dates[r.date()] = [{'opens': time_to_dtz(day.opens, arr=r),
                                'closes': time_to_dtz(day.closes, arr=r)}
                               for day in period.range_days
                               if day.weekday is r.weekday()]

        if exception_periods:
            # For period's exceptional periods, generate a new dict for those days
            exception_dates = {}
            for exception_period in exception_periods:
                # Exceptions happen inside date range of their periods so same mulling of start and end days occur
                if period.start < begin_dt.date():
                    start = begin_dt
                else:
                    start = arrow.get(period.start)
                if period.end > end_dt.date():
                    end = end_dt
                else:
                    end = arrow.get(period.end)

                # Updating dict of exceptional dates with current exception period's days
                for r in arrow.Arrow.range('day', start, end):
                    exception_dates[r.date()] = [{'opens': time_to_dtz(day.opens, arr=r),
                                                  'closes': time_to_dtz(day.closes, arr=r)}
                                                 for day in exception_period.range_days
                                                 if day.weekday is r.weekday()]

            # And override full day list with exceptions where applicable
            dates.update(exception_dates)

    # Old format for memory, does not quite cut it for resources with intermittent open/closed periods during one day
    # These would be places that close for lunch, for instance
    # date_list.append({'date': date.isoformat(), 'opens': opens, 'closes': closes})

    return dates


class Period(models.Model):
    """
    A period of time to express state of open or closed
    Days that specifies the actual activity hours link here
    """
    parent = models.ForeignKey('Period', verbose_name=_('exception parent period'), null=True, blank=True, editable=False)
    exception = models.BooleanField(verbose_name=_('Exceptional period'), default=False)
    resource = models.ForeignKey('Resource', verbose_name=_('Resource'), db_index=True,
                                 null=True, blank=True, related_name='periods')
    unit = models.ForeignKey('Unit', verbose_name=_('Unit'), db_index=True,
                             null=True, blank=True, related_name='periods')

    start = models.DateField(verbose_name=_('Start date'))
    end = models.DateField(verbose_name=_('End date'))
    duration = pgfields.DateRangeField(verbose_name=_('Length of period'), null=True,
                                       blank=True, db_index=True)

    name = models.CharField(max_length=200, verbose_name=_('Name'))
    description = models.CharField(verbose_name=_('Description'), null=True,
                                   blank=True, max_length=500)
    closed = models.BooleanField(verbose_name=_('Closed'), default=False, editable=False)

    class Meta:
        verbose_name = _("period")
        verbose_name_plural = _("periods")

    def __str__(self):
        # FIXME: output date in locale-specific format
        return "{0}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}".format(self.name, self.start, self.end, STATE_BOOLS[self.closed])

    # def save(self, *args, **kwargs):
    #     if (self.resource is not None and self.unit is not None) or \
    #             (self.resource is None and self.unit is None):
    #         raise ValidationError(_("You must set either 'resource' or 'unit', but not both"))
    #     if self.start and self.end:
    #         if self.start == self.end:
    #             # Range of 1 day must end on next day
    #             self.duration = DateRange(self.start,
    #                                       self.end + datetime.timedelta(days=+1))
    #         else:
    #             self.duration = DateRange(self.start, self.end)
    #     return super(Period, self).save(*args, **kwargs)

    def _validate_overlaps(self):
        if self.resource:
            old_periods = self.resource.periods
        else:
            old_periods = self.unit.periods

        # period has an end during the time range
        ends_during = dbm.Q(end__gte=self.start, end__lte=self.end)

        # period has a start during time range
        starts_during = dbm.Q(start__gte=self.start, start__lte=self.end)

        # period starts before and ends after time range
        larger = dbm.Q(start__lte=self.start, end__gte=self.end)

        # if any of these preceding rules is true, period has days on time range
        overlapping_periods_old = old_periods.filter(starts_during | ends_during | larger)

        if self.start > self.end:
            raise ValidationError("Period must start before its end", code="invalid_date_range")
        elif self.start == self.end:
            # DateRange must end at least one day after its start
            d_range = DateRange(self.start, self.end + datetime.timedelta(days=+1))
        else:
            d_range = DateRange(self.start, self.end)

        overlapping_periods = old_periods.filter(duration__overlap=d_range).exclude(pk=self.pk)

        #  Validate periods are not overlapping regular or exceptional periods
        if self.exception:
            overlapping_exceptions = overlapping_periods.filter(exception=True)
            if overlapping_exceptions:
                raise ValidationError(
                    "There is already an exceptional period on these dates",
                    code="multiple_exceptions"
                )
            regular_periods = overlapping_periods.filter(exception=False)
            if len(regular_periods) > 1:
                raise ValidationError(
                    "Exceptional period can't be exception for more than one period",
                    code="exception_for_multiple_periods"
                )
            elif not regular_periods:
                raise ValidationError(
                    "Exceptional period can't be exception without a regular period",
                    code="no_regular_period"
                )
            elif len(regular_periods) == 1:
                parent = regular_periods.first()
                if (parent.start <= self.start) and (parent.end >= self.end):
                    # period that encompasses this exceptional period is also this period's parent
                    self.parent = parent
                    # continue out of this layer of tests
                else:
                    raise ValidationError(
                        "Exception period can't have different times from its regular period",
                        code="larger_exception_than_parent"
                    )
            else:  # pragma: no cover
                raise ValidationError("Somehow exceptional period is too exceptional")
        else:
            self.parent = None  # Not an exception? Reset any parentage
            if overlapping_periods:
                raise ValidationError("There is already a period on these dates", code="overlap")

    def _validate_belonging(self):
        if not (self.resource_id or self.unit_id):
            raise ValidationError(_("You must set 'resource' or 'unit'"), code="no_belonging")

        if self.resource_id and self.unit_id:
            raise ValidationError(_("You must set either 'resource' or 'unit', but not both"), code="invalid_belonging")

    def _check_closed(self):
        if self.pk:
            # The period is not `closed` if it has any `open` days
            self.closed = not self.days.filter(closed=False).exists()
        else:  # Unsaved period, thus has no days, thus is closed.
            self.closed = True

    def clean(self):
        super(Period, self).clean()
        self._validate_belonging()
        self._validate_overlaps()
        self._check_closed()

    def save(self, *args, **kwargs):
        # Periods are either regular and stand alone or exceptions to regular period and must have a relation to it

        self.clean()

        if self.start == self.end:
            # Range of 1 day must end on next day
            self.duration = DateRange(self.start, self.end + datetime.timedelta(days=+1))
        else:
            self.duration = DateRange(self.start, self.end)

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

    period = models.ForeignKey(Period, verbose_name=_('Period'), db_index=True, related_name='days')
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
