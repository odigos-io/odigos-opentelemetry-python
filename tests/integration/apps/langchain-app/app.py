import os
from flask import Flask
from langchain_openai import ChatOpenAI

app = Flask(__name__)

MOCK_URL = os.environ.get("OPENAI_BASE_URL", "http://mock-llm-server:5000/v1")


@app.route("/test")
def test():
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        base_url=MOCK_URL,
        api_key="fake-key",
    )
    response = llm.invoke("Say hello")
    return {"status": "ok", "response": response.content}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
