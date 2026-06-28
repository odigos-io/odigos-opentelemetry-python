import logging
import random

from django.http import HttpResponse

logger = logging.getLogger(__name__)


def rolldice(request):
    logger.debug("DJANGO-DEBUG-OK")
    return HttpResponse(str(random.randint(1, 6)))
