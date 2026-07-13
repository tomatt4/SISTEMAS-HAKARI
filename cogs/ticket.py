import discord
from discord.ext import commands
from discord import app_commands

TICKET_IMAGE = "https://cdn.discordapp.com/attachments/1371703468879908978/1525624742596317354/file-00000000d6d4720ea48cb1e2df023032.png?ex=6a541043&is=6a52bec3&hm=a2086d1eebc16cc23f5ebd6d64670584c"
SUPPORT_ROLE_ID = 1512285548583190648


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="abrir ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="ticket_open_button"
    )
    async def ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild

        if guild is None:
            await interaction.followup.send(
                "isso só funciona dentro de um servidor.",
                ephemeral=True
            )
            return

        channel_name = f"ticket-{interaction.user.id}"

        existing = discord.utils.get(guild.text_channels, name=channel_name)

        if existing:
            await interaction.followup.send(
                f"você já possui um ticket aberto: {existing.mention}",
                ephemeral=True
            )
            return

        support_role = guild.get_role(SUPPORT_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True
            )
        }

        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                read_message_history=True
            )

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic="comando **/fechar** pra fechar o ticket"
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "não consegui criar o canal. falta permissão de **Gerenciar Canais** ou permissão na categoria.",
                ephemeral=True
            )
            return

        except discord.HTTPException as e:
            await interaction.followup.send(
                f"deu erro ao criar o canal:\n```py\n{e}\n```",
                ephemeral=True
            )
            return

        except Exception as e:
            await interaction.followup.send(
                f"erro inesperado ao criar o ticket:\n```py\n{e}\n```",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=".",
            description=(
                "> <:1359841749643694234:1512948491524243558> enquanto espera seu suporte, descreva seu problema brevemente no ticket.\n\n"
                "> <:1359841749643694234:1512948491524243558> **não** abra vários tickets ao mesmo tempo! seja paciente em esperar a administração."
            ),
            color=0xffffff
        )

        embed.set_image(url="https://cdn.discordapp.com/attachments/1371703468879908978/1525624742596317354/file-00000000d6d4720ea48cb1e2df023032.png?ex=6a541043&is=6a52bec3&hm=a2086d1eebc16cc23f5ebd6d64670584c")

        mention_text = interaction.user.mention

        if support_role:
            mention_text += f" {support_role.mention}"

        await channel.send(
            content=mention_text,
            embed=embed
        )

        await interaction.followup.send(
            f"seu ticket foi criado: {channel.mention}",
            ephemeral=True
        )


class CloseTicketView(discord.ui.View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel

    @discord.ui.button(
        label="confirmar",
        style=discord.ButtonStyle.green,
        emoji="✅",
        custom_id="ticket_close_confirm"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        try:
            await self.channel.delete()
        except Exception as e:
            await interaction.followup.send(
                f"não consegui fechar o ticket:\n```py\n{e}\n```",
                ephemeral=True
            )

    @discord.ui.button(
        label="cancelar",
        style=discord.ButtonStyle.red,
        emoji="❌",
        custom_id="ticket_close_cancel"
    )
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="cancelado",
            description="ticket não será fechado",
            color=discord.Color.red()
        )

        embed.set_footer(
            text="se tu quiser fechar ele, é só rodar o mesmo comando e clicar em confirmar"
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketView())

    @commands.command(name="painel")
    @commands.has_permissions(administrator=True)
    async def painel_prefix(self, ctx):
        embed = discord.Embed(
            title=".",
            description=(
                "> <:1359841749643694234:1512948491524243558> precisa de um help aí? clique no botão abaixo para abrir um ticket.\n\n"

                
                "> <:1359841749643694234:1512948491524243558> **não** abra vários tickets ao mesmo tempo! o limite é 1 ticket por usuário.\n\n"

                "> <:seta:1512948491524243558> solicitar parceria **__NÃO É AQUI__.** https://discord.com/channels/1490679537019654294/1498055324073197689."
            ),
            color=0xffffff
        )

        if TICKET_IMAGE:
            embed.set_image(url=TICKET_IMAGE)

        await ctx.send(embed=embed, view=TicketView())

    @app_commands.command(name="painel", description="Envia o painel de tickets")
    @app_commands.checks.has_permissions(administrator=True)
    async def painel_slash(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎫 sistema de tickets",
            description="clique no botão abaixo para abrir um ticket",
            color=discord.Color.blurple()
        )

        if TICKET_IMAGE:
            embed.set_image(url=TICKET_IMAGE)

        await interaction.response.send_message(embed=embed, view=TicketView())

    @commands.command(name="fechar")
    async def fechar_prefix(self, ctx):
        if not ctx.channel.name.startswith("ticket-"):
            embed = discord.Embed(
                title="❌ erro",
                description="este comando só pode ser usado em canais de ticket",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        support_role = ctx.guild.get_role(SUPPORT_ROLE_ID)

        if support_role not in ctx.author.roles and not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ epa pera aí amigão",
                description="só administradores ou suporte podem fechar o ticket",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="⚠️ confirmação de fechamento",
            description="quer mesmo fechar este ticket?",
            color=discord.Color.yellow()
        )

        await ctx.send(embed=embed, view=CloseTicketView(ctx.channel))

    @app_commands.command(name="fechar", description="Fecha um ticket")
    async def fechar_slash(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            embed = discord.Embed(
                title="❌ erro",
                description="este comando só pode ser usado em canais de ticket!",
                color=discord.Color.red()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID)

        if support_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ pera aí",
                description="só administradores ou suporte podem fechar o ticket",
                color=discord.Color.red()
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️ confirmação de fechamento",
            description="tem certeza que deseja fechar este ticket?",
            color=discord.Color.yellow()
        )

        await interaction.response.send_message(
            embed=embed,
            view=CloseTicketView(interaction.channel),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
