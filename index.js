import os
import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive
import asyncio
from discord.errors import HTTPException

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()

# Bot com suporte a prefixo e slash commands
bot = commands.Bot(command_prefix=",", intents=intents)

# Sistema anti-spam (erro 529)
class RateLimitHandler:
    def __init__(self):
        self.retry_count = 0
        self.max_retries = 5
        self.base_delay = 1
    
    async def handle_rate_limit(self, retry_after):
        """Aguarda e trata rate limit com retry exponencial"""
        wait_time = max(retry_after, self.base_delay * (2 ** self.retry_count))
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
        print(f"❌ Erro ao sincronizar slash commands: {e}")
    
    print(f'✅ Logado como {bot.user}')
    # Status do bot
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Criado por Salvador | Ligado 24/7"
        )
    )
    rate_limit_handler.reset()

@bot.event
async def on_error(event, *args, **kwargs):
    """Manipulador de erros para detectar e tratar rate limits"""
    import traceback
    import sys
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    if exc_type == HTTPException:
        if exc_value.status == 429:
            print(f"⚠️ Erro 429 (Rate Limit) detectado!")
            retry_after = getattr(exc_value, 'retry_after', 60)
            await rate_limit_handler.handle_rate_limit(retry_after)
    
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_cogs()
        keep_alive()
        await bot.start(TOKEN)

asyncio.run(main())
