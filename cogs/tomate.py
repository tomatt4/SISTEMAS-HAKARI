import discord
from discord.ext import commands
from discord import app_commands
import random
import time

cooldowns = {}

bloquear_tomates = False
bot_owner_id_cache = None

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


async def is_bot_owner(bot: commands.Bot, user_id: int):
    global bot_owner_id_cache

    if bot_owner_id_cache is None:
        app = await bot.application_info()
        bot_owner_id_cache = app.owner.id

    return user_id == bot_owner_id_cache


async def tomate_core(
    channel,
    author: discord.Member,
    send,
    target_user: discord.Member | None = None
):

    cooldown_time = get_cooldown(author)

    if cooldown_time > 0:
        last_used = cooldowns.get(author.id)

        if last_used:
            remaining = cooldown_time - (time.time() - last_used)

            if remaining > 0:
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)

                await send(
                    f"⏳ cooldown ativo. Espera **{minutes}m {seconds}s**"
                )
                return

        cooldowns[author.id] = time.time()

    if target_user is not None:
        if not can_pick_target(author):
            await send("tu não tem cargo pra escolher alvo do tomate 😭")
            return

        messages = [
            msg async for msg in channel.history(limit=50)
            if not msg.author.bot and msg.author.id == target_user.id
        ]

        if not messages:
            await send(
                f"não achei mensagem recente de {target_user.mention} pra tacar tomate"
            )
            return

        selected_msg = random.choice(messages)
        target = selected_msg.author

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

        guild = self.bot.get_guild(payload.guild_id)

        if bloquear_tomates and guild is not None:
            bot_owner = await is_bot_owner(self.bot, message.author.id)
            server_owner = message.author.id == guild.owner_id

            if bot_owner or server_owner:
                try:
                    user = await self.bot.fetch_user(payload.user_id)
                    await message.remove_reaction(payload.emoji, user)
                except discord.Forbidden:
                    pass
                except Exception:
                    pass

                return

        if message.author.id != self.bot.user.id:
            return

        try:
            user = await self.bot.fetch_user(payload.user_id)

            await message.remove_reaction(payload.emoji, user)

            await channel.send(
                f"E RAPÁ {user.mention} TÁ ACHANDO QUE TU É O REI DA COCADA PRETA É? pode tirando esse tomte aí de mim bestão, só **EU** posso tacar tomates por aqui."
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

    @app_commands.command(
        name="bloquear_tomates",
        description="Bloqueia tomates nas mensagens do dono do servidor e do dono do bot"
    )
    async def bloquear_tomates_slash(
        self,
        interaction: discord.Interaction
    ):
        global bloquear_tomates

        guild = interaction.guild

        if guild is None:
            await interaction.response.send_message(
                "esse comando só funciona em servidores.",
                ephemeral=True
            )
            return

        is_server_owner = interaction.user.id == guild.owner_id
        is_application_owner = await is_bot_owner(self.bot, interaction.user.id)

        if not is_server_owner and not is_application_owner:
            await interaction.response.send_message(
                "só o dono do servidor ou o dono do bot podem usar este comando.",
                ephemeral=True
            )
            return

        bloquear_tomates = not bloquear_tomates

        status = "ativado" if bloquear_tomates else "desativado"

        await interaction.response.send_message(
            f"🍅 bloqueio de tomates **{status}**",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Tomate(bot))
