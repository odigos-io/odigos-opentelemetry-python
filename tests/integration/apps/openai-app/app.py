import os
from flask import Flask
from openai import OpenAI

app = Flask(__name__)

MOCK_URL = os.environ.get("OPENAI_BASE_URL", "http://mock-llm-server:5000/v1")
client = OpenAI(base_url=MOCK_URL, api_key="fake-key")


@app.route("/test")
def test():
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
    )
    return {"status": "ok", "response": response.choices[0].message.content}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
