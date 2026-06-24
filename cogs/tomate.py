import discord
from discord.ext import commands
from discord import app_commands
import random
import time
import json
import os

cooldowns = {}

STAFF_ROLES = {
    1500969290093039626,  # Gerente
    1513653295061798922   # Staff
}

COOLDOWN = 15 * 60  # 15 minutos
tomate_hits = {}
TOMATE_FILE = "tomate_ranking.json"


def load_tomates():
    global tomate_hits

    if os.path.exists(TOMATE_FILE):
        with open(TOMATE_FILE, "r", encoding="utf-8") as f:
            tomate_hits = json.load(f)


def save_tomates():
    with open(TOMATE_FILE, "w", encoding="utf-8") as f:
        json.dump(tomate_hits, f, indent=4)

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
                    f"⏳ cooldown ativo (**15 minutos**)"
                )
                return

        cooldowns[author.id] = time.time()

    # Procura mensagens
    messages = [
        msg async for msg in channel.history(limit=5)
        if not msg.author.bot
    ]

    if not messages:
        await send("não achei mensagem pra tacar tomate")
        return

    selected_msg = random.choice(messages)
    target = selected_msg.author

    # Caso acerte um staff/gerente
    if isinstance(target, discord.Member) and is_staff(target):
        try:
            await selected_msg.add_reaction("🍅")

            target_id = str(target.id)
            tomate_hits[target_id] = tomate_hits.get(target_id, 0) + 1
            save_tomates()
            
            await send(
                "eta porra taquei nos staffs / gerentes do servidor, vou tomar ban nao ne administraçao"
            )
        except discord.Forbidden:
            await send(
                "não tenho permissão pra reagir mensagens pô"
            )
        return

    chance = random.randint(1, 100)

    # 35%
    if chance <= 35:
        await send(
            f"**RARO**(**CHANCE: 35%**): {target.mention} desviou do tomate"
        )
        return

    # 10%
    elif chance <= 45:
        await send(
            f"**SUPER RARO**(**CHANCE: 10%**): {target.mention} deu parry e jogou de volta em {author.mention}"
        )
        return

    # 5%
    elif chance <= 50:
        await send(
            f"**ULTRA RARO**(**CHANCE: 5%**): {target.mention} puxou uma KATANA e cortou o tomate AO MEIO no AR."
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

            target_id = str(target.id)
            tomate_hits[target_id] = tomate_hits.get(target_id, 0) + 1
            save_tomates()

            if target.id == author.id:
                await send(
                    f"{author.mention} tentou jogar um tomate e acabou acertando a si mesmo KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKJ"
                )
            else:
                await send(
                    f"{target.mention} foi atingido pelo tomate"
                )

        except discord.Forbidden:
            await send(
                "não tenho permissão pra reagir mensagens caralho"
            )

        except Exception as e:
            await send(
                f"erro ao lançar tomate: `{e}`"
            )


class Tomate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ranking_tomate",
        description="Mostra o top 10 pessoas que mais tomaram tomate"
    )
    async def ranking_tomate(
        self,
        interaction: discord.Interaction
    ):

        if not tomate_hits:
            await interaction.response.send_message(
                "ninguém tomou tomate ainda 🍅"
            )
            return

        ranking = sorted(
            tomate_hits.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        texto = "🍅 **TOP 10 MAIS TOMATADOS DO SERVIDOR** 🍅\n\n"

        for pos, (user_id, quantidade) in enumerate(
            ranking,
            start=1
        ):
            user = interaction.guild.get_member(
                int(user_id)
            )

            if user:
                nome = user.mention
            else:
                nome = f"usuário `{user_id}`"

            texto += (
                f"**top {pos}** - {nome} tomou "
                f"**{quantidade} tomates**\n"
            )

        await interaction.response.send_message(
            texto
        )
        
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
                f"E RAPÁ {user.mention} TÁ ACHANDO QUE TU É O REI DA COCADA PRETA É? pode tirando esse tomte aí de mim bestão, só **EU** posso tacar tomates por aqui."
            )

        except discord.Forbidden:
            await channel.send(
                "CADÊ MINHA PERMISSÃO DE TIRAR REAÇÃO PORRAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
            )
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
    load_tomates()
    await bot.add_cog(Tomate(bot))
