import discord
from discord.ext import commands

class Teste(commands.cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.hybrid_command(name="sohakari")
  async def teste (self, ctx):
    await ctx.send("so hakari")

async def setup(bot):
  await bot.add_cog(Teste(bot))
