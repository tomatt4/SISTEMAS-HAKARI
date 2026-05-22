import datetime
from typing import Optional

import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _can_act(self, ctx: commands.Context, member: discord.Member) -> tuple[bool, str]:
        if member == ctx.author:
            return False, "Você não pode usar esse comando em si mesmo."
        if member.top_role >= ctx.author.top_role and ctx.guild.owner_id != ctx.author.id:
            return False, "Você não pode agir em alguém com cargo igual ou superior ao seu."
        if member.top_role >= ctx.me.top_role:
            return False, "O bot não tem cargo suficiente para agir nesse membro."
        return True, ""

    def _parse_duration(self, duration: str) -> Optional[int]:
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        amount = duration[:-1]
        unit = duration[-1:].lower()
        if not amount.isdigit() or unit not in multipliers:
            return None
        return int(amount) * multipliers[unit]

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Sem motivo informado"):
        allowed, message = self._can_act(ctx, member)
        if not allowed:
            return await ctx.send(message)

        embed = discord.Embed(
            title="⚠️ Aviso",
            description=f"{member.mention} foi avisado.",
            color=discord.Color.gold()
        )
        embed.add_field(name="Motivo", value=reason, inline=False)
        embed.set_footer(text=f"Aviso por {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

        try:
            await member.send(f"Você foi avisado em {ctx.guild.name}. Motivo: {reason}")
        except discord.Forbidden:
            pass

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, duration: str, *, reason: str = "Sem motivo informado"):
        allowed, message = self._can_act(ctx, member)
        if not allowed:
            return await ctx.send(message)

        seconds = self._parse_duration(duration)
        if seconds is None:
            return await ctx.send("Use uma duração válida, por exemplo: `10m`, `1h`, `30s`.")

        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason=reason)
        except Exception as exc:
            return await ctx.send(f"Não foi possível mutar: {exc}")

        await ctx.send(f"🔇 {member.mention} foi mutado por {duration}. Motivo: {reason}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Sem motivo informado"):
        allowed, message = self._can_act(ctx, member)
        if not allowed:
            return await ctx.send(message)

        try:
            await member.kick(reason=reason)
        except Exception as exc:
            return await ctx.send(f"Não foi possível expulsar: {exc}")

        await ctx.send(f"👢 {member.mention} foi expulso. Motivo: {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Sem motivo informado"):
        allowed, message = self._can_act(ctx, member)
        if not allowed:
            return await ctx.send(message)

        try:
            await member.ban(reason=reason)
        except Exception as exc:
            return await ctx.send(f"Não foi possível banir: {exc}")

        await ctx.send(f"⛔ {member.mention} foi banido. Motivo: {reason}")

async def setup(bot):
    await bot.add_cog(Admin(bot))