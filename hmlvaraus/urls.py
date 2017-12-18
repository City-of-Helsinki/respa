from respa.urls import *
from hmlvaraus import admin

urlpatterns += [
    url(r'^sysadmin/', include(admin.site.urls)),
    url(r'^$', IndexView.as_view()),
]