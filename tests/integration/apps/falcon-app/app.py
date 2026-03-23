import falcon
import random


class RollDiceResource:
    def on_get(self, req, resp):
        resp.text = str(random.randint(1, 6))
        resp.status = falcon.HTTP_200


app = falcon.App()
app.add_route("/rolldice", RollDiceResource())

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
