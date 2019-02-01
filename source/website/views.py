from django.shortcuts import render


def home(request):
    return render(request, "home.html")


def pippo(request):
    return render(request, "pippo.html")


from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def lab(request):
    return render(request, "lab.html")
