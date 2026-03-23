import tornado.ioloop
import tornado.web
import random


class RollDiceHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(str(random.randint(1, 6)))


def make_app():
    return tornado.web.Application([
        (r"/rolldice", RollDiceHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()
