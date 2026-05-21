import discord
from discord.ext import commands

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def serverinfo(self, ctx):

        guild = ctx.guild

        embed = discord.Embed(
            title=f"🏰 {guild.name}",
            color=discord.Color.orange()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(
            name="👑 Dono",
            value=str(guild.owner),
            inline=False
        )

        embed.add_field(
            name="👥 Membros",
            value=guild.member_count,
            inline=True
        )

        embed.add_field(
            name="🚀 Boosts",
            value=guild.premium_subscription_count,
            inline=True
        )

        embed.add_field(
            name="⭐ Nível Boost",
            value=guild.premium_tier,
            inline=True
        )

        embed.add_field(
            name="📆 Criado em",
            value=guild.created_at.strftime("%d/%m/%Y"),
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
