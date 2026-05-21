import os
import discord
from discord.ext import commands
from keep_alive import keep_alive

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()

bot = commands.Bot(command_prefix=",", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Logado como {bot.user}')

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_cogs()
        keep_alive()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
