import os
from flask import Flask
import anthropic

app = Flask(__name__)

MOCK_URL = os.environ.get("ANTHROPIC_BASE_URL", "http://mock-llm-server:5000")
client = anthropic.Anthropic(base_url=MOCK_URL, api_key="fake-key")


@app.route("/test")
def test():
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=256,
        messages=[{"role": "user", "content": "Say hello"}],
    )
    return {"status": "ok", "response": message.content[0].text}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
