from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from config import BotConfig, load_config
from keep_alive import keep_alive

COGS = (
    "cogs.support_tickets",
    "cogs.user_info",
    "cogs.server_info",
    "cogs.tomato",
)


class SupportBot(commands.Bot):
    def __init__(self, config: BotConfig) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=config.prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        self.config_data = config

    async def setup_hook(self) -> None:
        for extension in COGS:
            await self.load_extension(extension)

        await self.tree.sync()

    async def on_ready(self) -> None:
        if self.user is None:
            return

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="tickets, tomates e infos",
        )
        await self.change_presence(activity=activity)
        print(f"Bot conectado como {self.user} (ID: {self.user.id})")

    async def on_command_error(
        self,
        ctx: commands.Context[commands.Bot],
        error: commands.CommandError,
    ) -> None:
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Voce nao tem permissao para usar esse comando.")
            return

        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("Esse comando so pode ser usado dentro de um servidor.")
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send("Nao consegui interpretar um dos argumentos enviados.")
            return

        logging.error(
            "Erro ao executar comando: %s",
            error,
            exc_info=(type(error), error, error.__traceback__),
        )
        await ctx.send("Aconteceu um erro inesperado ao executar esse comando.")


async def run_bot() -> None:
    config = load_config()
    keep_alive(config.port)

    bot = SupportBot(config)
    async with bot:
        await bot.start(config.token)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass
