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


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Exibe a latência da API do Discord"""
        latency = round(self.bot.latency * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Latência da API: **{latency}ms** | Ligado 24/7 com **Render** e **UptimeRobot**",
            color=discord.Color.green() if latency < 100 else discord.Color.yellow() if latency < 200 else discord.Color.red()
        )
        
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
    await bot.add_cog(UserInfo(bot))
    await bot.add_cog(Utilities(bot))
