import discord
from discord.ext import commands
from discord import app_commands
from components import ServerInfoEmbed, UserInfoEmbed, PingEmbed, HelpEmbed

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="serverinfo")
    async def serverinfo_prefix(self, ctx):
        """Exibe informações do servidor (prefixo)"""
        embeds = await ServerInfoEmbed(ctx.guild)
        await ctx.send(embeds=embeds)

    @app_commands.command(name="serverinfo", description="Exibe informações do servidor")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        """Exibe informações do servidor (slash)"""
        embeds = await ServerInfoEmbed(interaction.guild)
        await interaction.response.send_message(embeds=embeds)


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo")
    async def userinfo_prefix(self, ctx, member: discord.Member = None):
        """Exibe informações de um usuário (prefixo)"""
        member = member or ctx.author
        embeds = await UserInfoEmbed(member)
        await ctx.send(embeds=embeds)

    @app_commands.command(name="userinfo", description="Exibe informações de um usuário")
    async def userinfo_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        """Exibe informações de um usuário (slash)"""
        member = member or interaction.user
        embeds = await UserInfoEmbed(member)
        await interaction.response.send_message(embeds=embeds)


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_prefix(self, ctx):
        """Exibe a latência da API do Discord (prefixo)"""
        latency = round(self.bot.latency * 1000)
        embed = await PingEmbed(latency)
        await ctx.send(embed=embed)

    @app_commands.command(name="ping", description="Exibe a latência da API do Discord")
    async def ping_slash(self, interaction: discord.Interaction):
        """Exibe a latência da API do Discord (slash)"""
        latency = round(self.bot.latency * 1000)
        embed = await PingEmbed(latency)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="ajuda")
    async def ajuda_prefix(self, ctx):
        """Exibe informações do bot e comandos disponíveis (prefixo)"""
        commands_list = []
        for cog in self.bot.cogs.values():
            for command in cog.get_commands():
                commands_list.append(f"`{self.bot.command_prefix}{command.name}` - {command.help or 'Sem descrição'}")
        
        embeds = await HelpEmbed(
            self.bot.user.name,
            self.bot.command_prefix,
            commands_list
        )
        await ctx.send(embeds=embeds)

    @app_commands.command(name="ajuda", description="Exibe informações do bot e comandos disponíveis")
    async def ajuda_slash(self, interaction: discord.Interaction):
        """Exibe informações do bot e comandos disponíveis (slash)"""
        commands_list = []
        for cog in self.bot.cogs.values():
            for command in cog.get_commands():
                commands_list.append(f"`{self.bot.command_prefix}{command.name}` - {command.help or 'Sem descrição'}")
        
        embeds = await HelpEmbed(
            self.bot.user.name,
            self.bot.command_prefix,
            commands_list
        )
        await interaction.response.send_message(embeds=embeds)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
    await bot.add_cog(UserInfo(bot))
    await bot.add_cog(Utilities(bot))
