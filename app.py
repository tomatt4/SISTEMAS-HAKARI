import os
import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive
import asyncio
from discord.errors import HTTPException
import random
from discord.ext import tasks

status_list = [
    "dis.gg/ccdv | /help",
    "hakari v2.9.0",
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

@tasks.loop(seconds=40)
async def trocar_status():
    # Troca o status do bot periodicamente
    await bot.change_presence(status=(random.choice(discord_status_list)), activity=discord.CustomActivity(name=random.choice(status_list)))
    
        
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()

# Bot com suporte a prefixo e slash commands
bot = commands.Bot(command_prefix=",", intents=intents)

# Sistema anti-spam (erro 429)
class RateLimitHandler:
    def __init__(self):
        self.retry_count = 0
        self.max_retries = 5
        self.base_delay = 1
    
    async def handle_rate_limit(self, retry_after):
        """Aguarda e trata rate limit com retry exponencial"""
        wait_time = max(retry_after or 0, self.base_delay * (2 ** self.retry_count))
        print(f"⏱️ Rate limit detectado! Aguardando {wait_time}s...")
        await asyncio.sleep(wait_time)
        self.retry_count += 1
        if self.retry_count > self.max_retries:
            self.retry_count = 0
    
    def reset(self):
        self.retry_count = 0
        
rate_limit_handler = RateLimitHandler()

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash commands sincronizados!")
    except Exception as e:
        print(f"❌ erro ao sincronizar slash commands: {e}")

    print(f'✅ Logado como {bot.user}')
    
    if not trocar_status.is_running():
            trocar_status.start()
        
    rate_limit_handler.reset()

@bot.event
async def on_error(event, *args, **kwargs):
    """Manipulador de erros para detectar e tratar rate limits"""
    import traceback
    import sys
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    # Verifica se é uma HTTPException com status 429 (rate limit)
    try:
        status_code = getattr(exc_value, 'status', None) or getattr(exc_value, 'code', None)
        if status_code == 429:
            print(f"⚠️ Erro 429 (Rate Limit) detectado!")
            # tenta obter retry_after do objeto quando disponível
            retry_after = getattr(exc_value, 'retry_after', 60)
            await rate_limit_handler.handle_rate_limit(retry_after)
    except Exception:
        # Se algo der errado ao checar status/exceção, apenas registra e segue
        pass
    
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    
async def load_cogs():
    """Carrega todos os cogs da pasta ./cogs"""
    cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")

    if not os.path.isdir(cogs_dir):
        print("⚠️ Diretório ./cogs não existe.")
        return

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            cog_name = f"cogs.{filename[:-3]}"

            try:
                try:
                    await bot.unload_extension(cog_name)
                except commands.ExtensionNotLoaded:
                    pass
                except Exception as e:
                    print(f"⚠️ Ao descarregar {cog_name}: {e}")

                await bot.load_extension(cog_name)
                print(f"✅ Cog carregada: {cog_name}")

            except Exception as e:
                print(f"❌ Erro ao carregar {cog_name}: {e}")

async def main():
    if not TOKEN:
        print("❌ Variável de ambiente TOKEN não encontrada. Defina o TOKEN para iniciar o bot.")
        return

    async with bot:
        await load_cogs()
        # Inicia o keep-alive passando a instância do bot para que a página consiga ler o latency/ping
        keep_alive(bot)
        await bot.start(TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⚠️ Encerrando...")
