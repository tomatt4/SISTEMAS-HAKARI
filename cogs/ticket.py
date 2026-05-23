import discord
from discord.ext import commands
from discord import app_commands
from components import TicketEmbed, TicketOpenedEmbed, ConfirmCloseTicketEmbed, TicketClosedEmbed, ErrorEmbed

TICKET_IMAGE = ""  # coloque a imagem depois
SUPPORT_ROLE_ID = 1504998108407398501  # ID do cargo de suporte

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.name}")

        if existing:
            await interaction.response.send_message(
                "Você já possui um ticket aberto.",
                ephemeral=True
            )
            return

        # Obter o cargo de suporte
        support_role = guild.get_role(SUPPORT_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True
            )
        }
        
        # Adicionar permissão de ver canal para o cargo de suporte
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True
            )

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        embed = TicketOpenedEmbed(interaction.user).build()
        
        # Mencionar o cargo de suporte
        mention_text = interaction.user.mention
        if support_role:
            mention_text += f" {support_role.mention}"

        await channel.send(
            content=mention_text,
            embed=embed
        )

        await interaction.response.send_message(
            f"Seu ticket foi criado: {channel.mention}",
            ephemeral=True
        )

class CloseTicketView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.red, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.channel.delete()

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.gray, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = TicketClosedEmbed().build()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===== PAINEL COMMAND =====
    @commands.command(name="painel")
    @commands.has_permissions(administrator=True)
    async def painel_prefix(self, ctx):
        """Envia o painel de tickets (prefixo)"""
        embed = TicketEmbed(TICKET_IMAGE).build()
        await ctx.send(embed=embed, view=TicketView())

    @app_commands.command(name="painel", description="Envia o painel de tickets")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_slash(self, interaction: discord.Interaction):
        """Envia o painel de tickets (slash)"""
        embed = TicketEmbed(TICKET_IMAGE).build()
        await interaction.response.send_message(embed=embed, view=TicketView())

    # ===== FECHAR COMMAND =====
    @commands.command(name="fechar")
    async def fechar_prefix(self, ctx):
        """Comando para fechar um ticket (prefixo)"""
        # Verificar se é um canal de ticket
        if not ctx.channel.name.startswith("ticket-"):
            embed = ErrorEmbed("❌ Erro", "Este comando só pode ser usado em canais de ticket!").build()
            await ctx.send(embed=embed)
            return

        # Obter o cargo de suporte
        support_role = ctx.guild.get_role(SUPPORT_ROLE_ID)
        
        # Verificar se o usuário tem o cargo de suporte
        if support_role not in ctx.author.roles:
            embed = ErrorEmbed("❌ Permissão Negada", "Só administradores podem usar o comando").build()
            await ctx.send(embed=embed)
            return

        # Criar embed de confirmação
        embed = ConfirmCloseTicketEmbed().build()
        await ctx.send(embed=embed, view=CloseTicketView(ctx.channel))

    @app_commands.command(name="fechar", description="Fecha um ticket")
    async def fechar_slash(self, interaction: discord.Interaction):
        """Comando para fechar um ticket (slash)"""
        # Verificar se é um canal de ticket
        if not interaction.channel.name.startswith("ticket-"):
            embed = ErrorEmbed("❌ Erro", "Este comando só pode ser usado em canais de ticket!").build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Obter o cargo de suporte
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
        
        # Verificar se o usuário tem o cargo de suporte
        if support_role not in interaction.user.roles:
            embed = ErrorEmbed("❌ Permissão Negada", "Só administradores podem usar o comando").build()
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Criar embed de confirmação
        embed = ConfirmCloseTicketEmbed().build()
        await interaction.response.send_message(embed=embed, view=CloseTicketView(interaction.channel))

async def setup(bot):
    await bot.add_cog(Tickets(bot))
