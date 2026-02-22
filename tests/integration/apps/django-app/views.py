import random

from django.http import HttpResponse


def rolldice(request):
    return HttpResponse(str(random.randint(1, 6)))
