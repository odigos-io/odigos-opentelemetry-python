from flask import Flask
import random

app = Flask(__name__)


@app.route("/rolldice")
def rolldice():
    return str(random.randint(1, 6))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
