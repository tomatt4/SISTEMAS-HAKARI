import discord
from discord.ext import commands

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):

        member = member or ctx.author

        embed = discord.Embed(
            title=f"👤 Informações de {member}",
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(
            name="🆔 ID",
            value=member.id,
            inline=False
        )

        embed.add_field(
            name="📅 Conta criada",
            value=member.created_at.strftime("%d/%m/%Y"),
            inline=True
        )

        embed.add_field(
            name="📥 Entrou no servidor",
            value=member.joined_at.strftime("%d/%m/%Y"),
            inline=True
        )

        embed.add_field(
            name="🤖 Bot?",
            value=str(member.bot),
            inline=True
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserInfo(bot))
