from django.contrib.auth import logout
from django.shortcuts import redirect
from django.http import HttpResponse

def custom_logout(request):
    logout(request)
    return redirect('login')

def favicon_view(request):
    return HttpResponse(status=204)
