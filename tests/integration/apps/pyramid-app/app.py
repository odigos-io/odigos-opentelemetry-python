from pyramid.config import Configurator
from pyramid.response import Response
import random


def rolldice(request):
    return Response(str(random.randint(1, 6)))


if __name__ == "__main__":
    with Configurator() as config:
        config.add_route("rolldice", "/rolldice")
        config.add_view(rolldice, route_name="rolldice")
        app = config.make_wsgi_app()

    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
