from flask import Flask, render_template
import random

app = Flask(__name__)


@app.route("/rolldice")
def rolldice():
    return render_template("dice.html", result=random.randint(1, 6))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
