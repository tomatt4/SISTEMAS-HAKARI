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

TARGET_PICK_ROLES = {
    1490679537032495297,
    1490782190064373983,
    1514699980538118164
}

REDUCED_COOLDOWN_ROLES = {
    1490679537032495299,
    1514687383474405588,
    1490679537032495295,
    *TARGET_PICK_ROLES
}

DEFAULT_COOLDOWN = 15 * 60
REDUCED_COOLDOWN = 10 * 60


def has_role(member: discord.Member, roles: set[int]):
    return any(role.id in roles for role in member.roles)


def is_staff(member: discord.Member):
    return has_role(member, STAFF_ROLES)


def can_pick_target(member: discord.Member):
    return is_staff(member) or has_role(member, TARGET_PICK_ROLES)


def get_cooldown(member: discord.Member):
    if is_staff(member):
        return 0

    if has_role(member, REDUCED_COOLDOWN_ROLES):
        return REDUCED_COOLDOWN

    return DEFAULT_COOLDOWN


async def tomate_core(channel, author, send, target_user: discord.Member | None = None):

    cooldown_time = get_cooldown(author)

    if cooldown_time > 0:
        last_used = cooldowns.get(author.id)

        if last_used:
            remaining = cooldown_time - (time.time() - last_used)

            if remaining > 0:
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)

                await send(
                    f"⏳ cooldown ativo. espere **{minutes}m {seconds}s**"
                )
                return

        cooldowns[author.id] = time.time()

    # Se escolheu alvo
    if target_user is not None:
        if not can_pick_target(author):
            await send("tu não tem cargo pra escolher alvo do tomate doidão")
            return

        messages = [
            msg async for msg in channel.history(limit=50)
            if not msg.author.bot and msg.author.id == target_user.id
        ]

        if not messages:
            await send(f"não achei mensagem recente pra tacar tomate")
            return

        selected_msg = random.choice(messages)
        target = selected_msg.author

    # Alvo aleatório
    else:
        messages = [
            msg async for msg in channel.history(limit=5)
            if not msg.author.bot
        ]

        if not messages:
            await send("não achei mensagem pra tacar tomate")
            return

        selected_msg = random.choice(messages)
        target = selected_msg.author

    if isinstance(target, discord.Member) and is_staff(target):
        try:
            await selected_msg.add_reaction("🍅")

            await send(
                "eta porra taquei nos staffs / gerentes do servidor, vou tomar ban nao ne administraçao"
            )
        except discord.Forbidden:
            await send("não tenho permissão pra reagir mensagens pô")
        return

    chance = random.randint(1, 100)

    if chance <= 35:
        await send(
            f"**RARO**(**CHANCE: 35%**): {target.mention} desviou do tomate"
        )
        return

    elif chance <= 45:
        await send(
            f"**SUPER RARO**(**CHANCE: 10%**): {target.mention} deu parry e jogou de volta em {author.mention}"
        )
        return

    elif chance <= 50:
        await send(
            f"**ULTRA RARO**(**CHANCE: 5%**): {target.mention} puxou uma KATANA e cortou o tomate AO MEIO no AR."
        )
        return

    elif chance <= 75:
        await send(
            "errei o tomate kkkkkkkkkkkkkkkkkkkkj depois eu tento de novo"
        )
        return

    else:
        try:
            await selected_msg.add_reaction("🍅")

            if target.id == author.id:
                await send(
                    f"{author.mention} tentou jogar um tomate e acabou acertando a si mesmo KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKJ"
                )
            else:
                await send(
                    f"{target.mention} foi atingido pelo tomate"
                )

        except discord.Forbidden:
            await send("não tenho permissão pra reagir mensagens caralho")

        except Exception as e:
            await send(f"erro ao lançar tomate: `{e}`")


class Tomate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "🍅":
            return

        if payload.user_id == self.bot.user.id:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except:
            return

        if message.author.id != self.bot.user.id:
            return

        try:
            user = await self.bot.fetch_user(payload.user_id)

            await message.remove_reaction(payload.emoji, user)

            await channel.send(
                f"sub 5 {user.mention} tentando tacar tomate no true mogger 🤣"
            )

        except discord.Forbidden:
            await channel.send(
                "CADÊ MINHA PERMISSÃO DE TIRAR REAÇÃO PORRAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            )

    @app_commands.command(
        name="tomate",
        description="Lança um tomate em uma mensagem aleatória ou em alguém específico"
    )
    @app_commands.describe(
        alvo="Usuário que você quer tacar tomate"
    )
    async def tomate_slash(
        self,
        interaction: discord.Interaction,
        alvo: discord.Member | None = None
    ):

        async def send(msg):
            if interaction.response.is_done():
                await interaction.followup.send(msg)
            else:
                await interaction.response.send_message(msg)

        await tomate_core(
            interaction.channel,
            interaction.user,
            send,
            alvo
        )

    @commands.command(name="tomate")
    async def tomate_prefix(
        self,
        ctx: commands.Context,
        alvo: discord.Member | None = None
    ):

        if ctx.author.bot:
            return

        async def send(msg):
            await ctx.send(msg)

        await tomate_core(
            ctx.channel,
            ctx.author,
            send,
            alvo
        )


async def setup(bot):
    await bot.add_cog(Tomate(bot))
