import django.dispatch

reservation_confirmed = django.dispatch.Signal(providing_args=['instance', 'user'])
reservation_modified = django.dispatch.Signal(providing_args=['instance', 'user'])
reservation_cancelled = django.dispatch.Signal(providing_args=['instance', 'user'])
