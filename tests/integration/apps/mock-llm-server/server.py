import time
import uuid
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return "ok"


@app.route("/v1/chat/completions", methods=["POST"])
def openai_chat_completions():
    body = request.get_json(silent=True) or {}
    model = body.get("model", "gpt-4o-mini")
    return jsonify({
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mock response from the fake LLM server.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 10,
            "total_tokens": 22,
        },
    })


@app.route("/v1/messages", methods=["POST"])
def anthropic_messages():
    body = request.get_json(silent=True) or {}
    model = body.get("model", "claude-3-5-sonnet-20241022")
    return jsonify({
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": "This is a mock Anthropic response.",
            }
        ],
        "model": model,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": 15,
            "output_tokens": 8,
        },
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
