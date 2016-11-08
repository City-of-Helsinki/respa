from collections import OrderedDict
from django import forms
from django.contrib.admin.options import InlineModelAdmin
from django.utils.translation import ugettext_lazy
from resources.models import Day, Period, Resource, Unit

DAYS_OF_WEEK_MAP = dict(Day.DAYS_OF_WEEK)
WEEKDAY_PREFIX = "wd-"


def prefix_weekday(weekday, name):
    return "%s%s-%s" % (WEEKDAY_PREFIX, weekday, name)


class DayFormlet(forms.ModelForm):
    class Meta:
        model = Day
        fields = ("opens", "closes",)
        # Could add `"closed"` if required


class PeriodModelFormDayHelper(object):
    # Helper required to be able to sanely render fields in the Django template language.
    # See `django.contrib.admin.helpers` for questionable inspiration.

    def __init__(self, form, weekday, day):
        self.form = form
        self.weekday = weekday
        self.day = day
        self.name = DAYS_OF_WEEK_MAP[weekday]
        formlet = DayFormlet(instance=day)
        fields = [(prefix_weekday(weekday, key), value) for (key, value) in formlet.fields.items()]
        for field_tuple in fields:
            field_tuple[1].required = False
            field_tuple[1].label = "%s: %s" % (self.name, field_tuple[1].label)
            if isinstance(field_tuple[1], forms.TimeField):  # pragma: no branch
                # (remove the no-branch above if adding new fields to the formlet)
                field_tuple[1].widget.attrs["placeholder"] = ugettext_lazy("HH:mm")
        self.initial = dict((prefix_weekday(weekday, key), value) for (key, value) in formlet.initial.items())
        self.fields = dict(fields)
        self.prefix = prefix_weekday(weekday, "")

    def get_day_data(self):
        return dict(
            (k.replace(self.prefix, ""), v)
            for (k, v)
            in self.form.cleaned_data.items()
            if k.startswith(self.prefix)
        )

    def save(self, period):
        day_data = self.get_day_data()
        if not (day_data["opens"] and day_data["closes"]):  # Missing both opens and closes: delete the Day
            period.days.filter(weekday=self.weekday).delete()
            return
        day = (period.days.filter(weekday=self.weekday).first() or Day(period=period, weekday=self.weekday))
        formlet = DayFormlet(instance=day, data=day_data)
        formlet.save()

    def __getitem__(self, item):
        if item.endswith("_field"):
            field_name = item.replace("_field", "")
            return self.form[prefix_weekday(self.weekday, field_name)]
        raise KeyError(item)


class PeriodModelForm(forms.ModelForm):
    """
    :type instance: Period
    """
    class Meta:
        model = Period
        fields = ("start", "end", "name")

    def __init__(self, **kwargs):
        super(PeriodModelForm, self).__init__(**kwargs)
        self.setup_day_fields()

    def setup_day_fields(self):
        period_days = {wd: Day(period=self.instance, weekday=wd) for wd in DAYS_OF_WEEK_MAP}
        if self.instance.pk:
            period_days.update({day.weekday: day for day in self.instance.days.all()})
        self.day_fields = OrderedDict()
        for wd, day in sorted(period_days.items()):
            helper = self.day_fields[wd] = PeriodModelFormDayHelper(form=self, weekday=wd, day=day)
            # Due to Django quirks, we'll have to update both fields and base_fields...
            self.fields.update(helper.fields)
            self.base_fields.update(helper.fields)
            self.initial.update(helper.initial)

    def save(self, commit=True):
        self.instance = super(PeriodModelForm, self).save(commit=commit)
        assert isinstance(self.instance, Period)

        def save_days():
            for wd, helper in self.day_fields.items():
                helper.save(period=self.instance)
            self.instance.save_closedness()

        if commit:
            save_days()
        else:
            self.save_m2m = save_days
        return self.instance


class PeriodInline(InlineModelAdmin):
    model = Period
    # DRY (PMF should be testable on its own, but Inlines override the form's fields/excludes with this)
    fields = PeriodModelForm._meta.fields
    exclude = PeriodModelForm._meta.exclude
    form = PeriodModelForm
    template = "admin/resources/period_inline.html"
    ordering = ("start",)

    def get_extra(self, request, obj=None, **kwargs):
        # Don't show any empty periods if there already are some (they can still be dynamically added).
        if obj and obj.pk:
            return (0 if obj.periods.exists() else 1)
        return 1

    def get_formset(self, request, obj=None, **kwargs):
        # Ensure that we don't attempt to convince Django that our Period model has "wd" fields -- it doesn't!
        kwargs["fields"] = list(f for f in PeriodModelForm().base_fields if not f.startswith(WEEKDAY_PREFIX))
        formset = super(PeriodInline, self).get_formset(request, obj, **kwargs)
        if obj:  # pragma: no branch
            if isinstance(obj, Unit):  # pragma: no branch
                formset.form.base_fields.pop("resource", None)
            elif isinstance(obj, Resource):  # pragma: no branch
                formset.form.base_fields.pop("unit", None)
        return formset
