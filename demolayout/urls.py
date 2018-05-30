from django.conf.urls import url
from django.shortcuts import render

def index(request):
    return render(request, 'layout.html')

app_name = 'helloworld'

urlpatterns = [
    url(r'^$', index)
]