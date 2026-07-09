import discord
from discord.ext import commands
from discord import app_commands

TICKET_IMAGE = "https://i.postimg.cc/C1xWFvcx/ae83e304bef29dcb77916303bf7961b5-gif-(500-225).gif"  # coloque a imagem depois
SUPPORT_ROLE_ID = 1504998108407398501  # ID do cargo de suporte

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="abrir ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.name}")

        if existing:
            await interaction.response.send_message(
                "você já possui um ticket aberto",
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
            overwrites=overwrites,
            description=f"ID do usuário: {interaction.user.id}"
        )

        embed = discord.Embed(
            title="ticket aberto",
            description=(
                "ㅤㅤㅤㅤㅤㅤㅤㅤㅤ__***boas vindas ao seu ticket!***\n"
                "ㅤㅤㅤㅤㅤ***enquanto espera a staff te atender, explique o motivo do seu ticket abaixo.***__"
            ),
            color=0xffffff
        )
        embed.set_image(url="https://i.postimg.cc/MGv7qV15/download-(1).gif")
        # Mencionar o cargo de suporte
        mention_text = interaction.user.mention
        if support_role:
            mention_text += f" {support_role.mention}"

        await channel.send(
            content=mention_text,
            embed=embed
        )

        await interaction.response.send_message(
            f"seu ticket foi criado: {channel.mention}",
            ephemeral=True
        )

class CloseTicketView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(label="confirmar", style=discord.ButtonStyle.sucess, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.channel.delete()

    @discord.ui.button(label="cancelar", style=discord.ButtonStyle.gray, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="cancelado",
            description="ticket não será fechado",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()
        embed.set_footer("se tu quiser fechar ele agora é só rodar o mesmo comando e clicar em confirmar")

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===== PAINEL COMMAND =====
    @commands.command(name="painel")
    @commands.has_permissions(administrator=True)
    async def painel_prefix(self, ctx):
        """Envia o painel de tickets (prefixo)"""
        embed = discord.Embed(
            title=".",
            description=(
                "ㅤㅤㅤㅤㅤㅤ__ ***boas vindas ao sistema de tickets!***\n\n"
                "ㅤㅤㅤㅤㅤㅤㅤㅤㅤ***aqui você pode tirar várias dúvidas que você tem sobre o nosso servidor.***\n\n"
                "ㅤㅤㅤ***sinta-se a vontade para ser atendido por um dos nossos staffs.***__"
            ),
            color=0xffffff
        )

        if TICKET_IMAGE:
            embed.set_image(url=TICKET_IMAGE)

        await ctx.send(embed=embed, view=TicketView())

    @app_commands.command(name="painel", description="Envia o painel de tickets")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_slash(self, interaction: discord.Interaction):
        """Envia o painel de tickets (slash)"""
        embed = discord.Embed(
            title="🎫 sistema de tickets",
            description="clique no botão abaixo para abrir um ticket",
            color=discord.Color.blurple()
        )

        if TICKET_IMAGE:
            embed.set_image(url=TICKET_IMAGE)

        await interaction.response.send_message(embed=embed, view=TicketView())

    # ===== FECHAR COMMAND =====
    @commands.command(name="fechar")
    async def fechar_prefix(self, ctx):
        """Comando para fechar um ticket (prefixo)"""
        # Verificar se é um canal de ticket
        if not ctx.channel.name.startswith("ticket-"):
            embed = discord.Embed(
                title="❌ erro",
                description="este comando só pode ser usado em canais de ticket",
                color=discord.Color.red(),

            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        # Obter o cargo de suporte
        support_role = ctx.guild.get_role(SUPPORT_ROLE_ID)
        
        # Verificar se o usuário tem o cargo de suporte
        if support_role not in ctx.author.roles:
            embed = discord.Embed(
                title="❌ epa pera aí amigão",
                description="só administradores podem fechar o ticket",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, ephemeral=True)
            return

        # Criar embed de confirmação
        embed = discord.Embed(
            title="⚠️ confirmação de fechamento",
            description="quer mesmo fechar este ticket?",
            color=discord.Color.yellow()
        )

        await ctx.send(embed=embed, view=CloseTicketView(ctx.channel), ephemeral=True)

    @app_commands.command(name="fechar", description="Fecha um ticket")
    async def fechar_slash(self, interaction: discord.Interaction):
        """Comando para fechar um ticket (slash)"""
        # Verificar se é um canal de ticket
        if not interaction.channel.name.startswith("ticket-"):
            embed = discord.Embed(
                title="❌ erro",
                description="este comando só pode ser usado em canais de ticket!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Obter o cargo de suporte
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)
        
        # Verificar se o usuário tem o cargo de suporte
        if support_role not in interaction.user.roles:
            embed = discord.Embed(
                title="❌ pera aí meu negão",
                description="só administradores podem fechar o ticket",
                color=discord.Color.red()

            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Criar embed de confirmação
        embed = discord.Embed(
            title="⚠️ confirmação de fechamento",
            description="tem certeza que deseja fechar este ticket?",
            color=discord.Color.yellow()
        )

        await interaction.response.send_message(embed=embed, view=CloseTicketView(interaction.channel), ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
