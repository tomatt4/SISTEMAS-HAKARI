from __future__ import annotations

import asyncio
import re

import discord
from discord.ext import commands

from config import BotConfig


def _safe_channel_name(base_name: str) -> str:
    clean_name = re.sub(r"[^a-z0-9-]", "-", base_name.lower())
    clean_name = re.sub(r"-{2,}", "-", clean_name).strip("-")
    return clean_name[:80] or "ticket"


class CloseTicketView(discord.ui.View):
    def __init__(self, config: BotConfig) -> None:
        super().__init__(timeout=None)
        self.config = config

    @discord.ui.button(
        label="Fechar ticket",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:close",
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button["CloseTicketView"],
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Esse botao so funciona dentro de um servidor.",
                ephemeral=True,
            )
            return

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "Esse botao so pode ser usado em canais de ticket.",
                ephemeral=True,
            )
            return

        topic = channel.topic or ""
        is_owner = topic == f"ticket-owner:{interaction.user.id}"
        is_admin = interaction.user.guild_permissions.administrator
        has_support_role = (
            self.config.support_role_id is not None
            and any(role.id == self.config.support_role_id for role in interaction.user.roles)
        )

        if not any((is_owner, is_admin, has_support_role)):
            await interaction.response.send_message(
                "Voce precisa ser o dono do ticket, admin ou suporte para fechar.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "Ticket sera fechado em 5 segundos.",
            ephemeral=True,
        )
        await asyncio.sleep(5)
        await channel.delete(reason=f"Ticket fechado por {interaction.user}")


class TicketPanelView(discord.ui.View):
    def __init__(self, bot: commands.Bot, config: BotConfig) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.config = config

    @discord.ui.button(
        label="Abrir ticket",
        style=discord.ButtonStyle.success,
        custom_id="ticket:create",
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button["TicketPanelView"],
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Esse botao so funciona dentro de um servidor.",
                ephemeral=True,
            )
            return

        existing_channel = discord.utils.find(
            lambda channel: isinstance(channel, discord.TextChannel)
            and channel.topic == f"ticket-owner:{interaction.user.id}",
            interaction.guild.channels,
        )
        if existing_channel is not None:
            await interaction.response.send_message(
                f"Voce ja tem um ticket aberto: {existing_channel.mention}",
                ephemeral=True,
            )
            return

        overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        me = interaction.guild.get_member(self.bot.user.id) if self.bot.user else None
        if me is not None:
            overwrites[me] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
            )

        if self.config.support_role_id is not None:
            support_role = interaction.guild.get_role(self.config.support_role_id)
            if support_role is not None:
                overwrites[support_role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                )

        category = (
            interaction.guild.get_channel(self.config.ticket_category_id)
            if self.config.ticket_category_id is not None
            else None
        )
        if not isinstance(category, discord.CategoryChannel):
            category = None

        ticket_channel = await interaction.guild.create_text_channel(
            name=_safe_channel_name(f"ticket-{interaction.user.name}"),
            topic=f"ticket-owner:{interaction.user.id}",
            overwrites=overwrites,
            category=category,
            reason=f"Ticket criado por {interaction.user}",
        )

        embed = discord.Embed(
            title="Ticket aberto com sucesso",
            description=(
                f"{interaction.user.mention}, descreva seu problema e aguarde a equipe responder.\n\n"
                "Quando tudo estiver resolvido, use o botao abaixo para fechar o ticket."
            ),
            color=discord.Color.green(),
        )
        if self.config.ticket_panel_image_url:
            embed.set_image(url=self.config.ticket_panel_image_url)

        await ticket_channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=CloseTicketView(self.config),
        )
        await interaction.response.send_message(
            f"Seu ticket foi criado em {ticket_channel.mention}.",
            ephemeral=True,
        )


class SupportTickets(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.config: BotConfig = bot.config_data
        self.registration_panel_view = TicketPanelView(bot, self.config)
        self.registration_close_view = CloseTicketView(self.config)

    async def cog_load(self) -> None:
        self.bot.add_view(self.registration_panel_view)
        self.bot.add_view(self.registration_close_view)

    @commands.hybrid_command(
        name="ticketpainel",
        description="Envia o painel para abrir tickets de suporte.",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def ticket_panel(self, ctx: commands.Context[commands.Bot]) -> None:
        embed = discord.Embed(
            title="Central de Suporte",
            description=(
                "Clique no botao abaixo para abrir um ticket privado com a equipe.\n"
                "Voce podera explicar seu problema e fechar o ticket quando terminar."
            ),
            color=discord.Color.blurple(),
        )
        if self.config.ticket_panel_image_url:
            embed.set_image(url=self.config.ticket_panel_image_url)

        embed.set_footer(text="Edite TICKET_PANEL_IMAGE_URL no .env para colocar sua imagem.")

        await ctx.send(embed=embed, view=TicketPanelView(self.bot, self.config))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SupportTickets(bot))

