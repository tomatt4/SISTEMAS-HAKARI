from __future__ import annotations

from threading import Thread

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def home() -> tuple[dict[str, str], int]:
    return jsonify({"status": "online", "service": "discord-bot"}), 200


def _run_web_server(port: int) -> None:
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


def keep_alive(port: int) -> Thread:
    thread = Thread(target=_run_web_server, args=(port,), daemon=True)
    thread.start()
    return thread

