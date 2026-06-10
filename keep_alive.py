# keep_alive.py
from flask import Flask, render_template_string
from threading import Thread
from datetime import datetime
import time

app = Flask(__name__)

start_time = time.time()
bot_instance = None

def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{days}d {hours}h {minutes}min"

@app.route("/")
def home():
    uptime = format_uptime(time.time() - start_time)

    if bot_instance:
        gateway_ping = round(bot_instance.latency * 1000)
    else:
        gateway_ping = None

    if gateway_ping is None:
        gateway_status = "Indisponível"
        gateway_class = "gray"
    elif gateway_ping < 150:
        gateway_status = "Rápida"
        gateway_class = "green"
    elif gateway_ping < 300:
        gateway_status = "Estável"
        gateway_class = "yellow"
    else:
        gateway_status = "Lenta"
        gateway_class = "red"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Status do Hakari</title>
        <style>
            body {{
                background: #0f0f0f;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 40px;
            }}

            .card {{
                background: #1b1b1b;
                padding: 25px;
                border-radius: 15px;
                max-width: 500px;
                margin: auto;
                box-shadow: 0 0 20px #00ff9955;
            }}

            .green {{ color: #00ff99; }}
            .yellow {{ color: #ffd500; }}
            .red {{ color: #ff4d4d; }}
            .gray {{ color: #aaa; }}

            .info {{
                background: #252525;
                margin: 12px 0;
                padding: 12px;
                border-radius: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Hakari Bot</h1>

            <div class="info">
                <strong>Status:</strong>
                <span class="green">Online</span>
            </div>

            <div class="info">
                <strong>Uptime:</strong> {uptime}
            </div>

            <div class="info">
                <strong>Gateway Discord:</strong>
                <span class="{gateway_class}">{gateway_status}</span>
                <br>
                <small>{gateway_ping if gateway_ping else "?"} ms</small>
            </div>

            <div class="info">
                <strong>Hospedagem:</strong> Render
            </div>

            <div class="info">
                <strong>Monitoramento 24/7:</strong> UptimeRobot
            </div>

            <p style="color:#888;">
                Página de status pública do bot.
            </p>
        </div>
    </body>
    </html>
    """

    return render_template_string(html)

def run():
    app.run(host="0.0.0.0", port=5000)

def keep_alive(bot=None):
    global bot_instance
    bot_instance = bot

    server = Thread(target=run)
    server.start()
