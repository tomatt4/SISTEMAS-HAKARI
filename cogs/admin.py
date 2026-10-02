import datetime
import json
import os
from typing import Optional

import asyncpg
import discord
from discord.ext import commands
from discord import app_commands

from .menu import DEVELOPER_ID

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _can_act(self, actor: discord.Member, target: discord.Member, guild: discord.Guild) -> tuple[bool, str]:
        """Verifica se um membro pode agir em outro"""
        if target == actor:
            return False, "<:wrong:1554659471223947324> você não pode usar punições contra si mesmo"
        if target.top_role >= actor.top_role and guild.owner_id != actor.id:
            return False, "<:wrong:1554659471223947324> você não pode agir em alguém com cargo igual ou superior ao seu"
        if target.top_role >= guild.me.top_role:
            return False, "<:wrong:1554659471223947324> o bot não tem cargo suficiente para agir nesse membro"
        return True, ""

    def _parse_duration(self, duration: str) -> Optional[int]:
        """Converte duração em segundos (ex: 10m, 1h, 30s)"""
        multipliers = {"sec": 1, "min": 60, "h": 3600, "d": 86400}
        try:
            amount = duration[:-1]
            unit = duration[-1:].lower()
            if not amount.isdigit() or unit not in multipliers:
                return None
            return int(amount) * multipliers[unit]
        except:
            return None

    # ===== WARN COMMAND =====
    @commands.command(name="warn")
    @commands.has_permissions(manage_roles=True)
    async def warn_prefix(self, ctx: commands.Context, member: discord.Member, *, reason: str = "sem motivo informado"):
        """Avisa um membro (prefixo)"""
        allowed, message = self._can_act(ctx.author, member, ctx.guild)
        if not allowed:
            return await ctx.send(message)

        embed = discord.Embed(
            title="⚠️ Aviso",
            description=f"{member.mention} foi avisado",
            color=discord.Color.gold()
        )
        embed.add_field(name="motivo", value=reason, inline=False)
        embed.set_footer(text=f"aviso por {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

        try:
            await member.send(f"você foi avisado em {ctx.guild.name}. Motivo: {reason}")
        except discord.Forbidden:
            pass

    @app_commands.command(name="warn", description="Avisa um membro")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Sem motivo informado"):
        """Avisa um membro (slash)"""
        allowed, message = self._can_act(interaction.user, member, interaction.guild)
        if not allowed:
            return await interaction.response.send_message(message, ephemeral=True)

        embed = discord.Embed(
            title="⚠️ Aviso",
            description=f"{member.mention} foi avisado",
            color=discord.Color.gold()
        )
        embed.add_field(name="Motivo", value=reason, inline=False)
        embed.set_footer(text=f"Aviso por {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

        try:
            await member.send(f"Você foi avisado em {interaction.guild.name}. Motivo: {reason}")
        except discord.Forbidden:
            pass

    # ===== MUTE COMMAND =====
    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute_prefix(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "Sem motivo informado"):
        """Muta um membro (prefixo)"""
        allowed, message = self._can_act(ctx.author, member, ctx.guild)
        if not allowed:
            return await ctx.send(message)

        seconds = self._parse_duration(duration)
        if seconds is None:
            return await ctx.send("use uma duração válida, por exemplo: `10min`, `1h`, `30sec`")

        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason=reason)
        except Exception as exc:
            return await ctx.send(f"não foi possível mutar: {exc}")

        await ctx.send(f"{member.mention} foi mutado por {duration}, motivo: {reason}")

    @app_commands.command(name="mute", description="Muta um membro")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Sem motivo informado"):
        """Muta um membro (slash)"""
        allowed, message = self._can_act(interaction.user, member, interaction.guild)
        if not allowed:
            return await interaction.response.send_message(message, ephemeral=True)

        seconds = self._parse_duration(duration)
        if seconds is None:
            return await interaction.response.send_message("use uma duração válida, por exemplo: `10min`, `1h`, `30sec`.", ephemeral=True)

        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason=reason)
        except Exception as exc:
            return await interaction.response.send_message(f"não foi possível mutar: {exc}", ephemeral=True)

        await interaction.response.send_message(f"{member.mention} foi mutado por {duration}, motivo: {reason}")

    # ===== KICK COMMAND =====
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_prefix(self, ctx: commands.Context, member: discord.Member, *, reason: str = "sem motivo informado"):
        """Expulsa um membro (prefixo)"""
        allowed, message = self._can_act(ctx.author, member, ctx.guild)
        if not allowed:
            return await ctx.send(message)

        try:
            await member.kick(reason=reason)
        except Exception as exc:
            return await ctx.send(f"não foi possível expulsar: {exc}")

        await ctx.send(f"{member.mention} foi expulso, motivo: {reason}")

    @app_commands.command(name="kick", description="Expulsa um membro")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "sem motivo informado"):
        """Expulsa um membro (slash)"""
        allowed, message = self._can_act(interaction.user, member, interaction.guild)
        if not allowed:
            return await interaction.response.send_message(message, ephemeral=True)

        try:
            await member.kick(reason=reason)
        except Exception as exc:
            return await interaction.response.send_message(f"não foi possível expulsar: {exc}", ephemeral=True)

        await interaction.response.send_message(f"{member.mention} foi expulso, motivo: {reason}")

    # ===== BAN COMMAND =====
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_prefix(self, ctx: commands.Context, member: discord.Member, *, reason: str = "sem motivo informado"):
        """Bane um membro (prefixo)"""
        allowed, message = self._can_act(ctx.author, member, ctx.guild)
        if not allowed:
            return await ctx.send(message)

        try:
            await member.ban(reason=reason)
        except Exception as exc:
            return await ctx.send(f"não foi possível banir: {exc}")

        await ctx.send(f"{member.mention} foi banido, motivo: {reason}")

    @app_commands.command(name="ban", description="Bane um membro")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "sem motivo informado"):
        """Bane um membro (slash)"""
        allowed, message = self._can_act(interaction.user, member, interaction.guild)
        if not allowed:
            return await interaction.response.send_message(message, ephemeral=True)

        try:
            await member.ban(reason=reason)
        except Exception as exc:
            return await interaction.response.send_message(f"mão foi possível banir: {exc}", ephemeral=True)

        await interaction.response.send_message(f"{member.mention} foi banido, motivo: {reason}")

    @commands.command(name="salvarcargos")
    async def save_roles_temporarily(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return await ctx.send("Este comando só pode ser usado em um servidor.")
        if ctx.author.id not in {ctx.guild.owner_id, DEVELOPER_ID}:
            return await ctx.send("Somente o dono do servidor ou o desenvolvedor do bot pode usar este comando.")

        upper_role = ctx.guild.get_role(1540034106270679110)
        lower_role = ctx.guild.get_role(1541324825380003930)
        if upper_role is None or lower_role is None:
            return await ctx.send("Não encontrei um ou ambos os cargos de referência neste servidor.")
        if upper_role.position <= lower_role.position:
            return await ctx.send("Os cargos de referência estão em ordem inválida.")

        database_url = os.getenv("DATABASE") or os.getenv("DATABASE_URL")
        if not database_url:
            return await ctx.send("A variável DATABASE não está definida no ambiente do bot.")

        roles = [
            role
            for role in ctx.guild.roles
            if lower_role.position < role.position < upper_role.position
        ]
        if not roles:
            return await ctx.send("Não há cargos entre os dois cargos de referência.")

        records = [
            (
                ctx.guild.id,
                role.id,
                json.dumps(
                    {
                        "name": role.name,
                        "position": role.position,
                        "permissions": role.permissions.value,
                        "color": role.color.value,
                        "hoist": role.hoist,
                        "mentionable": role.mentionable,
                        "managed": role.managed,
                    }
                ),
            )
            for role in roles
        ]
        try:
            async with asyncpg.create_pool(
                dsn=database_url,
                ssl="require",
                min_size=1,
                max_size=2,
                command_timeout=20,
            ) as pool:
                await pool.execute(
                    """
                    CREATE TABLE IF NOT EXISTS temporary_role_backups (
                        guild_id BIGINT NOT NULL,
                        role_id BIGINT NOT NULL,
                        role_data JSONB NOT NULL,
                        captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (guild_id, role_id)
                    )
                    """
                )
                await pool.executemany(
                    """
                    INSERT INTO temporary_role_backups (guild_id, role_id, role_data)
                    VALUES ($1, $2, $3::jsonb)
                    ON CONFLICT (guild_id, role_id) DO UPDATE SET
                        role_data = EXCLUDED.role_data,
                        captured_at = NOW()
                    """,
                    records,
                )
        except Exception as error:
            print(
                f"Falha ao salvar cargos no DATABASE: {type(error).__name__}: {error}",
                flush=True,
            )
            return await ctx.send("Não consegui conectar ou salvar no banco. Consulte os logs do bot.")
        await ctx.send(f"Salvei {len(roles)} cargo(s) no DATABASE.")


async def setup(bot):
    await bot.add_cog(Admin(bot))