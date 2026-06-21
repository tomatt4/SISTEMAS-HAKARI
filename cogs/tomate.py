import discord
from discord.ext import commands
from discord import app_commands
import random
import time

cooldowns = {}

STAFF_ROLES = {
    1500969290093039626,  # Gerente
    1513653295061798922   # Staff
}

COOLDOWN = 15 * 60  # 15 minutos


def is_staff(member: discord.Member):
    return any(role.id in STAFF_ROLES for role in member.roles)


async def tomate_core(channel, author, send):

    # Cooldown (staff não pega)
    if not is_staff(author):
        last_used = cooldowns.get(author.id)

        if last_used:
            remaining = COOLDOWN - (time.time() - last_used)

            if remaining > 0:
                await send(
                    f"⏳ espere {int(remaining)} segundos para usar novamente (cooldown de **15 minutos**)"
                )
                return

        cooldowns[author.id] = time.time()

    # Procura mensagens
    messages = [
        msg async for msg in channel.history(limit=5)
        if not msg.author.bot
    ]

    if not messages:
        await send("🍅 não achei mensagem pra tacar tomate")
        return

    selected_msg = random.choice(messages)
    target = selected_msg.author

    # Caso acerte um staff/gerente
    if isinstance(target, discord.Member) and is_staff(target):
        try:
            await selected_msg.add_reaction("🍅")
            await send(
                "LASCOU, joguei o tomate em um dos STAFFS / GERENTES do servidor😭"
            )
        except discord.Forbidden:
            await send(
                "❌ não tenho permissão pra reagir mensagens pô"
            )
        return

    chance = random.randint(1, 100)

    # 35%
    if chance <= 35:
        await send(
            f"**RARO**(**CHANCE: 35%**): {target.mention} desviou do tomate!"
        )
        return

    # 10%
    elif chance <= 45:
        await send(
            f"**SUPER RARO**(**CHANCE: 10%**): {target.mention} deu parry e jogou de volta em {author.mention}!"
        )
        return

    # 5%
    elif chance <= 50:
        await send(
            f"**ULTRA RARO**(**CHANCE: 5%**): {target.mention} puxou uma KATANA e cortou o tomate AO MEIO no AR☠️☠️☠️"
        )
        return

    # 25%
    elif chance <= 75:
        await send(
            "errei o tomate kkkkkkkkkkkkkkkkkkkkj depois eu tento de novo"
        )
        return

    # 25%
    else:
        try:
            await selected_msg.add_reaction("🍅")

            if target.id == author.id:
                await send(
                    f"☠️ {author.mention} tentou jogar um tomate e acabou acertando a si mesmo KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK"
                )
            else:
                await send(
                    f"🍅 {target.mention} foi atingido pelo tomate"
                )

        except discord.Forbidden:
            await send(
                "❌ não tenho permissão pra reagir mensagens caralho"
            )

        except Exception as e:
            await send(
                f"❌ erro ao lançar tomate: `{e}`"
            )


class Tomate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Slash Command
    @app_commands.command(
        name="tomate",
        description="Lança um tomate em uma mensagem aleatória"
    )
    async def tomate_slash(
        self,
        interaction: discord.Interaction
    ):

        async def send(msg):
            if interaction.response.is_done():
                await interaction.followup.send(msg)
            else:
                await interaction.response.send_message(msg)

        await tomate_core(
            interaction.channel,
            interaction.user,
            send
        )

    # Prefix Command
    @commands.command(name="tomate")
    async def tomate_prefix(
        self,
        ctx: commands.Context
    ):

        if ctx.author.bot:
            return

        async def send(msg):
            await ctx.send(msg)

        await tomate_core(
            ctx.channel,
            ctx.author,
            send
        )


async def setup(bot):
    await bot.add_cog(Tomate(bot))
