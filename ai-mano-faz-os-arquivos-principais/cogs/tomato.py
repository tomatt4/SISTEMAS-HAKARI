from __future__ import annotations

import time

import discord
from discord.ext import commands


class Tomato(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cooldowns: dict[int, float] = {}
        self.cooldown_seconds = 300

    def _remaining_cooldown(self, user_id: int) -> int:
        last_use = self.cooldowns.get(user_id)
        if last_use is None:
            return 0

        elapsed = time.monotonic() - last_use
        remaining = self.cooldown_seconds - elapsed
        return max(0, int(remaining))

    @commands.hybrid_command(
        name="tomate",
        description="Joga tomates nas 5 mensagens mais recentes do chat.",
    )
    @commands.guild_only()
    async def tomato(self, ctx: commands.Context[commands.Bot]) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            await ctx.send("Esse comando so pode ser usado dentro de um servidor.")
            return

        is_admin = ctx.author.guild_permissions.administrator
        if not is_admin:
            remaining = self._remaining_cooldown(ctx.author.id)
            if remaining > 0:
                minutes, seconds = divmod(remaining, 60)
                await ctx.send(
                    f"Espere {minutes}m {seconds:02d}s para usar o tomate novamente."
                )
                return

            self.cooldowns[ctx.author.id] = time.monotonic()

        recent_messages: list[discord.Message] = []
        async for message in ctx.channel.history(limit=10):
            if ctx.message is not None and message.id == ctx.message.id:
                continue

            recent_messages.append(message)
            if len(recent_messages) == 5:
                break

        if not recent_messages:
            await ctx.send("Nao encontrei mensagens recentes suficientes para jogar tomates.")
            return

        reacted_messages = 0
        for message in recent_messages:
            try:
                await message.add_reaction("\U0001F345")
                reacted_messages += 1
            except discord.HTTPException:
                continue

        await ctx.send(f"Joguei tomates em {reacted_messages} mensagem(ns) recentes.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Tomato(bot))
