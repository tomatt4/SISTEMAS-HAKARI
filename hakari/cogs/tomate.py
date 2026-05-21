import discord
import random
import time
from discord.ext import commands

cooldowns = {}

class Tomato(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def tomate(self, ctx):

        if not ctx.author.guild_permissions.administrator:

            last_used = cooldowns.get(ctx.author.id)

            if last_used:
                remaining = 300 - (time.time() - last_used)

                if remaining > 0:
                    await ctx.send(
                        f"pera ai uns {int(remaining)} segundos pra jogar de novo bro"
                    )
                    return

            cooldowns[ctx.author.id] = time.time()

        messages = [msg async for msg in ctx.channel.history(limit=5)]

        emojis = ["🍅"]

        for msg in messages:

            try:
                await msg.reply(
                    f""
                )
            except:
                pass

        await ctx.send("tomate lançado com sucesso")

async def setup(bot):
    await bot.add_cog(Tomato(bot))
