from helusers.admin import *
from hmlvaraus.models import hml_reservation, berth


class HMLReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation',)

class BerthAdmin(admin.ModelAdmin):
    list_display = ('resource',)

admin.site.register(hml_reservation.HMLReservation, HMLReservationAdmin)
admin.site.register(berth.Berth, BerthAdmin)


