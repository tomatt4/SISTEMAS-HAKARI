from __future__ import annotations

import discord
from discord.ext import commands


class ServerInfo(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="serverinfo",
        description="Mostra informacoes do servidor atual.",
    )
    @commands.guild_only()
    async def server_info(self, ctx: commands.Context[commands.Bot]) -> None:
        guild = ctx.guild
        if guild is None:
            await ctx.send("Esse comando so pode ser usado em um servidor.")
            return

        fetched_guild = await self.bot.fetch_guild(guild.id, with_counts=True)
        owner = guild.owner or await self.bot.fetch_user(guild.owner_id)
        owner_display = getattr(owner, "mention", str(owner))

        human_members = sum(1 for member in guild.members if not member.bot)
        bot_members = sum(1 for member in guild.members if member.bot)

        embed = discord.Embed(
            title=f"Informacoes do servidor: {guild.name}",
            color=discord.Color.gold(),
            description=guild.description or "Esse servidor nao possui descricao configurada.",
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="ID", value=str(guild.id), inline=True)
        embed.add_field(name="Dono", value=owner_display, inline=True)
        embed.add_field(
            name="Criado em",
            value=discord.utils.format_dt(guild.created_at, style="F"),
            inline=False,
        )
        embed.add_field(
            name="Membros",
            value=str(guild.member_count or fetched_guild.approximate_member_count or 0),
            inline=True,
        )
        embed.add_field(name="Humanos", value=str(human_members), inline=True)
        embed.add_field(name="Bots", value=str(bot_members), inline=True)
        embed.add_field(name="Canais de texto", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Canais de voz", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="Categorias", value=str(len(guild.categories)), inline=True)
        embed.add_field(name="Cargos", value=str(len(guild.roles)), inline=True)
        embed.add_field(
            name="Nivel de impulsos",
            value=f"Nivel {guild.premium_tier}",
            inline=True,
        )
        embed.add_field(
            name="Quantidade de impulsos",
            value=str(guild.premium_subscription_count or 0),
            inline=True,
        )
        embed.add_field(
            name="Nivel de verificacao",
            value=str(guild.verification_level).replace("_", " ").title(),
            inline=True,
        )
        embed.add_field(
            name="Banner",
            value=fetched_guild.banner.url if fetched_guild.banner else "Esse servidor nao possui banner.",
            inline=False,
        )

        if fetched_guild.banner:
            embed.set_image(url=fetched_guild.banner.url)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ServerInfo(bot))
