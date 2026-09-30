import asyncio
import random
from discord.ext import commands

class Resenha(commands.Cog):
    def __init__(self, bot)
        self.bot = bot

    @commands.command(name="averiguar", help="AVERIGUANDO RESENHA")
    async def averiguar(self, ctx):
        mensagem = await ctx.send("<a:loading:1554658916741283990> averiguando a resenha do chat...")

        await asyncio.sleep(5)

        opcoes = [
            "<:correct:1554659481512841267> Resenha confirmada com sucesso.",
            "<:wrong:1554659471223947324> Resenha tá fraca hoje."
        ]

        escolha = random.choice(opcoes)

        await mensagem.edit(content=f"{escolha}")

async def setup(bot)
    await bot.add_cog(Resenha(bot))