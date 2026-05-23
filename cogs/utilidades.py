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
        embed = ServerInfoEmbed(ctx.guild).build()
        await ctx.send(embed=embed)

    @app_commands.command(name="serverinfo", description="Exibe informações do servidor")
    async def serverinfo_slash(self, interaction: discord.Interaction):
        """Exibe informações do servidor (slash)"""
        embed = ServerInfoEmbed(interaction.guild).build()
        await interaction.response.send_message(embed=embed)


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="userinfo")
    async def userinfo_prefix(self, ctx, member: discord.Member = None):
        """Exibe informações de um usuário (prefixo)"""
        member = member or ctx.author
        embed = UserInfoEmbed(member).build()
        await ctx.send(embed=embed)

    @app_commands.command(name="userinfo", description="Exibe informações de um usuário")
    async def userinfo_slash(self, interaction: discord.Interaction, member: discord.Member = None):
        """Exibe informações de um usuário (slash)"""
        member = member or interaction.user
        embed = UserInfoEmbed(member).build()
        await interaction.response.send_message(embed=embed)


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_prefix(self, ctx):
        """Exibe a latência da API do Discord (prefixo)"""
        latency = round(self.bot.latency * 1000)
        embed = PingEmbed(latency).build()
        await ctx.send(embed=embed)

    @app_commands.command(name="ping", description="Exibe a latência da API do Discord")
    async def ping_slash(self, interaction: discord.Interaction):
        """Exibe a latência da API do Discord (slash)"""
        latency = round(self.bot.latency * 1000)
        embed = PingEmbed(latency).build()
        await interaction.response.send_message(embed=embed)

    @commands.command(name="ajuda")
    async def ajuda_prefix(self, ctx):
        """Exibe informações do bot e comandos disponíveis (prefixo)"""
        # Construir lista de comandos
        commands_list = []
        for cog in self.bot.cogs.values():
            for command in cog.get_commands():
                commands_list.append(f"`{self.bot.command_prefix}{command.name}` - {command.help or 'Sem descrição'}")
        
        commands_text = "\n".join(commands_list[:20]) if commands_list else "Nenhum comando encontrado"
        
        embed = HelpEmbed(
            self.bot.user.name,
            self.bot.command_prefix,
            commands_text
        ).build()
        
        await ctx.send(embed=embed)

    @app_commands.command(name="ajuda", description="Exibe informações do bot e comandos disponíveis")
    async def ajuda_slash(self, interaction: discord.Interaction):
        """Exibe informações do bot e comandos disponíveis (slash)"""
        # Construir lista de comandos
        commands_list = []
        for cog in self.bot.cogs.values():
            for command in cog.get_commands():
                commands_list.append(f"`{self.bot.command_prefix}{command.name}` - {command.help or 'Sem descrição'}")
        
        commands_text = "\n".join(commands_list[:20]) if commands_list else "Nenhum comando encontrado"
        
        embed = HelpEmbed(
            self.bot.user.name,
            self.bot.command_prefix,
            commands_text
        ).build()
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
    await bot.add_cog(UserInfo(bot))
    await bot.add_cog(Utilities(bot))
