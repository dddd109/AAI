"""
Anthropic -> OpenAI translation proxy for Claude Code.
Usage: proxy_server.py [port]
Start SSH tunnel first: ssh -f -N -L 8080:localhost:8080 gdut
"""
import json, sys, time, os
from flask import Flask, request, jsonify
import urllib.request
import urllib.error

BACKEND = "http://localhost:8080/v1"
app = Flask(__name__)


@app.route("/health", methods=["GET"])
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "backend": BACKEND})


@app.route("/v1/messages", methods=["POST"])
def messages():
    try:
        body = request.get_json(force=True)

        # Anthropic -> OpenAI message conversion
        messages = []
        sys_msg = body.get("system", "")
        if isinstance(sys_msg, str) and sys_msg.strip():
            messages.append({"role": "system", "content": sys_msg})

        for m in body.get("messages", []):
            content = m.get("content", "")
            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict):
                        if c.get("type") == "text":
                            parts.append(c.get("text", ""))
                content = " ".join(parts)
            messages.append({"role": m.get("role", "user"), "content": str(content)})

        # Use urllib (NOT requests) to avoid proxy env issues
        payload = json.dumps({
            "messages": messages,
            "max_tokens": body.get("max_tokens", 4096),
            "temperature": body.get("temperature", 0.7),
        }).encode("utf-8")

        # Create opener that ignores proxy
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)

        req = urllib.request.Request(
            f"{BACKEND}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = opener.open(req, timeout=180)
        rd = json.loads(resp.read())
        txt = rd["choices"][0]["message"]["content"]

        return jsonify({
            "id": f"msg_{int(time.time() * 1000)}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": txt}],
            "model": body.get("model", "qwen2.5-coder-32b"),
            "stop_reason": rd["choices"][0].get("finish_reason", "stop"),
            "usage": rd.get("usage", {}),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "id": f"err_{int(time.time() * 1000)}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": f"[Server LLM unavailable: {e}]"}],
            "model": "error",
            "stop_reason": "error",
            "usage": {},
        }), 502


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    print(f"Proxy: http://127.0.0.1:{port} -> {BACKEND}")
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
