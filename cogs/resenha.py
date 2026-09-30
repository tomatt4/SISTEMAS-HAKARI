import asyncio
import random
from discord.ext import commands

class Resenha(commands.Cog):
    def __init__(self, bot)
        self.bot = bot

    @commands.command(name="averiguar", help="AVERIGUANDO RESENHA")
    async def averiguar(self, ctx):
        mensagem = await ctx.send("Averiguando a resenha do chat...")

        await asyncio.sleep(3)

        opcoes = [
            "Resenha tá forte.",
            "Resenha tá fraca hoje."
        ]

        escolha = random.choice(opcoes)

        await mensagem.edit(content=f"{escolha}")

async def setup(bot)
    await bot.add_cog(Resenha(bot))