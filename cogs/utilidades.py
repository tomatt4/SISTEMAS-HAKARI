import discord
from discord.ext import commands, tasks
from discord import app_commands

SUPPORT_ROLE_ID = 1500969290093039626
SUPPORT_CHANNEL_ID = 1490679537888006192


class SupportStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_message = None
        self.last_status = None
        self.check_support_status.start()

    def cog_unload(self):
        self.check_support_status.cancel()

    async def update_support_status(self):
        channel = self.bot.get_channel(SUPPORT_CHANNEL_ID)

        if channel is None:
            try:
                channel = await self.bot.fetch_channel(SUPPORT_CHANNEL_ID)
            except:
                return

        guild = channel.guild
        role = guild.get_role(SUPPORT_ROLE_ID)

        if role is None:
            return

        staffs_online = sum(
            1
            for member in role.members
            if not member.bot and member.status != discord.Status.offline
        )

        suporte_online = staffs_online > 0

        novo_status = "on" if suporte_online else "off"

        if suporte_online:
            nova_mensagem = f"suporte ativo: **{staffs_online} staff(s) online**."
        else:
            nova_mensagem = "suporte inativo: não tem staff online kkkkkkkkkkkkkkj."

        if self.last_status == novo_status:
            return

        if self.last_message:
            try:
                await self.last_message.delete()
            except:
                pass

        async for msg in channel.history(limit=20):
            if msg.author == self.bot.user and msg.content in ["suporte on: staffs online", "suporte off: tem nenhum staff online kkkkkkj"]:
                try:
                    await msg.delete()
                except:
                    pass

        self.last_message = await channel.send(nova_mensagem)
        self.last_status = novo_status

    @tasks.loop(seconds=30)
    async def check_support_status(self):
        await self.update_support_status()

    @check_support_status.before_loop
    async def before_check_support_status(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        if any(role.id == SUPPORT_ROLE_ID for role in after.roles):
            await self.update_support_status()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        before_roles = {role.id for role in before.roles}
        after_roles = {role.id for role in after.roles}

        if SUPPORT_ROLE_ID in before_roles or SUPPORT_ROLE_ID in after_roles:
            await self.update_support_status()


class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverinfo")
    async def serverinfo_prefix(self, ctx):
        guild = ctx.guild

        embed = discord.Embed(
            title=f"🏰 {guild.name}",
            color=discord.Color.orange()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="👑 Dono com Posse", value=str(guild.owner), inline=False)
        embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
        embed.add_field(name="🚀 Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="⭐ Nível Boost", value=guild.premium_tier, inline=True)
        embed.add_field(name="📆 Criado em", value=guild.created_at.strftime("%d/%m/%Y"), inline=False)

        await ctx.send(embed=embed)

    @app_commands.command(name="serverinfo", description="Exibe informações do servidor")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        guild = interaction.guild

        embed = discord.Embed(
            title=f"🏰 {guild.name}",
            color=discord.Color.orange()
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="👑 Dono com Posse", value=str(guild.owner), inline=False)
        embed.add_field(name="👥 Membros", value=guild.member_count, inline=True)
        embed.add_field(name="🚀 Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="⭐ Nível Boost", value=guild.premium_tier, inline=True)
        embed.add_field(name="📆 Criado em", value=guild.created_at.strftime("%d/%m/%Y"), inline=False)

        await interaction.response.send_message(embed=embed)


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo")
    async def userinfo_prefix(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        embed = discord.Embed(
            title=f"👤 Informações de {member}",
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 ID", value=member.id, inline=False)
        embed.add_field(name="📅 Conta criada", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="📥 Entrou no servidor", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🤖 Bot?", value=str(member.bot), inline=True)

        await ctx.send(embed=embed)

    @app_commands.command(name="userinfo", description="Exibe informações de um usuário")
    async def userinfo_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        embed = discord.Embed(
            title=f"👤 Informações de {member}",
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🆔 ID", value=member.id, inline=False)
        embed.add_field(name="📅 Conta criada", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="📥 Entrou no servidor", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
        embed.add_field(name="🤖 Bot?", value=str(member.bot), inline=True)

        await interaction.response.send_message(embed=embed)


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_prefix(self, ctx):
        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 pong!",
            description=f"latência da API: **{latency} milissegundos** | ligado 24/7 com **Render** e **UptimeRobot**",
            color=discord.Color.green() if latency < 100 else discord.Color.yellow() if latency < 200 else discord.Color.red()
        )

        await ctx.send(embed=embed)

    @app_commands.command(name="ping", description="Exibe a latência da API do Discord")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 pong!",
            description=f"latência da API: **{latency} milissegundos** | ligado 24/7 com **Render** e **UptimeRobot**",
            color=discord.Color.green() if latency < 100 else discord.Color.yellow() if latency < 200 else discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
    await bot.add_cog(UserInfo(bot))
    await bot.add_cog(Utilities(bot))
    await bot.add_cog(SupportStatus(bot))
