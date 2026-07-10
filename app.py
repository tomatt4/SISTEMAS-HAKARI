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
        await self.load_cogs()

        try:
            guild = discord.Object(id=GUILD_ID)

            comandos_servidor = await self.tree.sync(guild=guild)
            comandos_globais = await self.tree.sync()

            print(
                f"✅ Slash commands sincronizados: "
                f"{len(comandos_servidor)} no servidor e "
                f"{len(comandos_globais)} globais."
            )

            print(
                "📌 Comandos do servidor:",
                [comando.name for comando in comandos_servidor]
            )

            print(
                "🌎 Comandos globais:",
                [comando.name for comando in comandos_globais]
            )

        except Exception as erro:
            print(
                f"❌ Erro ao sincronizar slash commands: "
                f"{type(erro).__name__}: {erro}"
            )

    async def load_cogs(self):
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")

        if not os.path.isdir(cogs_dir):
            print("⚠️ Diretório ./cogs não existe.")
            return

        for filename in os.listdir(cogs_dir):
            if not filename.endswith(".py"):
                continue

            if filename.startswith("__"):
                continue

            cog_name = f"cogs.{filename[:-3]}"

            try:
                await self.load_extension(cog_name)
                print(f"✅ Cog carregada: {cog_name}")

            except commands.ExtensionAlreadyLoaded:
                await self.reload_extension(cog_name)
                print(f"🔄 Cog recarregada: {cog_name}")

            except Exception as erro:
                print(
                    f"❌ Erro ao carregar {cog_name}: "
                    f"{type(erro).__name__}: {erro}"
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
        print("❌ Variável TOKEN não encontrada.")
        return

    if not APPLICATION_ID:
        print("❌ Variável APPLICATION_ID não encontrada.")
        return

    keep_alive(bot)

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⚠️ Encerrando...")
