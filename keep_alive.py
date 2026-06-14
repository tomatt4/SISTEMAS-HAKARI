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
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Status do Hakari</title>

    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            min-height: 100vh;
            background:
                radial-gradient(circle at top, #173d2d 0%, transparent 35%),
                linear-gradient(135deg, #080808, #111111);
            color: white;
            font-family: Arial, Helvetica, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 25px;
        }}

        .card {{
            width: 100%;
            max-width: 620px;
            background: rgba(27, 27, 27, 0.92);
            border: 1px solid rgba(0, 255, 153, 0.25);
            border-radius: 22px;
            padding: 32px;
            box-shadow: 0 0 35px rgba(0, 255, 153, 0.18);
            backdrop-filter: blur(10px);
            animation: fadeIn 0.7s ease;
        }}

        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(18px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        h1 {{
            font-size: clamp(1.8rem, 5vw, 2.5rem);
            margin-bottom: 8px;
            color: #00ff99;
        }}

        .subtitle {{
            color: #aaa;
            margin-bottom: 26px;
            font-size: 0.95rem;
        }}

        .info {{
            background: #222;
            margin: 14px 0;
            padding: 16px 18px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            transition: 0.25s ease;
            border: 1px solid transparent;
        }}

        .info:hover {{
            transform: translateY(-3px) scale(1.01);
            border-color: rgba(0, 255, 153, 0.35);
            background: #282828;
            box-shadow: 0 8px 22px rgba(0, 255, 153, 0.12);
        }}

        .label {{
            color: #ddd;
            font-weight: bold;
        }}

        .value {{
            text-align: right;
            font-weight: 600;
        }}

        .ping {{
            display: block;
            font-size: 0.8rem;
            color: #999;
            margin-top: 3px;
        }}

        .green {{ color: #00ff99; }}
        .yellow {{ color: #ffd500; }}
        .red {{ color: #ff4d4d; }}
        .gray {{ color: #aaa; }}

        .status-dot {{
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ff99;
            border-radius: 50%;
            margin-right: 7px;
            box-shadow: 0 0 12px #00ff99;
        }}

        .footer {{
            margin-top: 24px;
            color: #888;
            font-size: 0.9rem;
            text-align: center;
        }}

        @media (max-width: 520px) {{
            body {{
                padding: 16px;
                align-items: flex-start;
                padding-top: 35px;
            }}

            .card {{
                padding: 24px 18px;
                border-radius: 18px;
            }}

            .info {{
                flex-direction: column;
                align-items: flex-start;
            }}

            .value {{
                text-align: left;
            }}
        }}
    </style>
</head>

<body>
    <main class="card">
        <h1>Status do Hakari</h1>
        <p class="subtitle">Informações públicas da hospedagem e conexão do bot.</p>

        <section class="info">
            <span class="label">Status</span>
            <span class="value green">
                <span class="status-dot"></span>Online
            </span>
        </section>

        <section class="info">
            <span class="label">Uptime</span>
            <span class="value">{uptime}</span>
        </section>

        <section class="info">
            <span class="label">Gateway Discord</span>
            <span class="value {gateway_class}">
                {gateway_status}
                <small class="ping">{gateway_ping if gateway_ping else "?"} ms</small>
            </span>
        </section>

        <section class="info">
            <span class="label">Hospedagem</span>
            <span class="value">Render</span>
        </section>

        <section class="info">
            <span class="label">Monitoramento 24/7</span>
            <span class="value">UptimeRobot</span>
        </section>
        
        <section class="info">
            <span class="label">API Discord(ms)</span>
            <span class="value"></span>
        </section>

        <p class="footer">
            Página de status pública do Hakari.
        </p>
    </main>
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
