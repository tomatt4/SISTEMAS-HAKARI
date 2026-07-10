import os
import asyncio
import random
import discord

from discord.ext import commands, tasks
from keep_alive import keep_alive


TOKEN = os.getenv("TOKEN", "").strip()
APPLICATION_ID = os.getenv("APPLICATION_ID", "").strip()

GUILD_ID = 1500231901397516340


status_list = [
    "dis.gg/ccdv | /help",
    "hakari v2.10.24",
    "feito por mattzaddas",
    "PORRA NORUEGA ESTUDOU O BRASIL",
    "meu prefixo é uma virgula ok",
    "six seven da silva bora bill",
    "pô man, as vezes cansa ser bot",
    "eu fico 24/7 com o uptime robot toda hora falando BORA TRABALHAR no meu http de monitoramento sabia",
    "NÃO, ERRO 429 DE NOVO NÃO POR FAVOR DEUS😭😭😭😭😭😭😭😭😭",
    "porra um dia eu fui apagado por inteiro porque o matt quis mudar de python pra javascript, que merda em",
    "ok, pelo visto acabei de tomar um jumpscare do erro 429 e fiquei off por 6 dias."
]

discord_status_list = [
    discord.Status.idle,
    discord.Status.dnd,
    discord.Status.online
]


intents = discord.Intents.all()


class HakariBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=",",
            intents=intents,
            application_id=int(APPLICATION_ID)
        )

    async def setup_hook(self):
    print("🔧 setup_hook iniciado.", flush=True)

    try:
        await self.load_cogs()
    except Exception as erro:
        print(
            f"❌ Erro geral ao carregar cogs: "
            f"{type(erro).__name__}: {erro}",
            flush=True
        )

    print(
        f"📦 Cogs atualmente carregadas: {list(self.cogs.keys())}",
        flush=True
    )

    try:
        guild = discord.Object(id=GUILD_ID)

        comandos_servidor = await self.tree.sync(guild=guild)
        print(
            f"✅ {len(comandos_servidor)} comandos sincronizados no servidor.",
            flush=True
        )

        comandos_globais = await self.tree.sync()
        print(
            f"✅ {len(comandos_globais)} comandos globais sincronizados.",
            flush=True
        )

    except Exception as erro:
        print(
            f"❌ Erro ao sincronizar comandos: "
            f"{type(erro).__name__}: {erro}",
            flush=True
        )

    async def load_cogs(self):
    cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")

    print(f"📁 Procurando cogs em: {cogs_dir}", flush=True)
    print(f"📁 Pasta existe: {os.path.isdir(cogs_dir)}", flush=True)

    if not os.path.isdir(cogs_dir):
        print("❌ Diretório cogs não encontrado.", flush=True)
        return

    arquivos = os.listdir(cogs_dir)
    print(f"📄 Arquivos encontrados: {arquivos}", flush=True)

    for filename in arquivos:
        if not filename.endswith(".py") or filename.startswith("__"):
            continue

        cog_name = f"cogs.{filename[:-3]}"

        try:
            await self.load_extension(cog_name)
            print(f"✅ Cog carregada: {cog_name}", flush=True)

        except Exception as erro:
            print(
                f"❌ Erro ao carregar {cog_name}: "
                f"{type(erro).__name__}: {erro}",
                flush=True
            )


bot = HakariBot()


@tasks.loop(seconds=40)
async def trocar_status():
    await bot.change_presence(
        status=random.choice(discord_status_list),
        activity=discord.CustomActivity(
            name=random.choice(status_list)
        )
    )


@trocar_status.before_loop
async def antes_de_trocar_status():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f"✅ Logado como {bot.user} | ID: {bot.user.id}")

    if not trocar_status.is_running():
        trocar_status.start()


@bot.event
async def on_error(event, *args, **kwargs):
    import traceback
    import sys

    print(f"❌ Erro não tratado no evento: {event}")

    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(
        exc_type,
        exc_value,
        exc_traceback
    )


async def main():
    if not TOKEN:
        raise RuntimeError("Variável TOKEN não encontrada.")

    if not APPLICATION_ID:
        raise RuntimeError("Variável APPLICATION_ID não encontrada.")

    print("1️⃣ Iniciando servidor Flask...", flush=True)
    keep_alive(bot)

    print("2️⃣ Flask iniciado. Preparando bot...", flush=True)

    try:
        async with bot:
            print("3️⃣ Chamando bot.start()...", flush=True)
            await bot.start(TOKEN.strip())

    except Exception as erro:
        print(
            f"❌ ERRO AO INICIAR O BOT: "
            f"{type(erro).__name__}: {erro}",
            flush=True
        )
        raise
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⚠️ Encerrando...")
