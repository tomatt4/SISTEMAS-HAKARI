import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import re

LOGS_CHANNEL_ID = 1502744433525788753
CONFISSOES_CHANNEL_ID = 1524861580217421834
DENUNCIAS_CHANNEL_ID = 1502744433525788753
TARGET_SERVER_ID = 1500231901397516340
MODERACAO_ROLE_ID = 1504998108407398501

GUILD = discord.Object(id=TARGET_SERVER_ID)
confissoes_map: dict[int, dict] = {}


async def get_channel(bot: commands.Bot, channel_id: int):
    """Pega canal pelo cache e, se não tiver no cache, busca pela API."""
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except Exception:
            return None
    return channel


async def safe_reply(interaction: discord.Interaction, content: str, *, ephemeral: bool = True):
    """Responde uma interaction sem estourar erro caso ela já tenha sido respondida."""
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral)


class ConfissaoModal(discord.ui.Modal, title="confissão anônima"):
    confissao = discord.ui.TextInput(
        label="sua confissão",
        placeholder="manda tua confissão aqui, mas sem quebrar as regras ☠️",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=4000,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        bot = interaction.client
        logs_channel = await get_channel(bot, LOGS_CHANNEL_ID)
        confissoes_channel = await get_channel(bot, CONFISSOES_CHANNEL_ID)

        if logs_channel is None or confissoes_channel is None:
            await safe_reply(interaction, "❌ não achei o canal de logs ou confissões. Avisa o Salva.")
            return

        confissao_text = str(self.confissao.value).strip()

        confissao_embed = discord.Embed(
            title="🔐 nova confissão anônima",
            description=f"confissão: {confissao_text}",
            color=discord.Color.dark_embed(),
        )
        confissao_embed.set_footer(text="as confissões são totalmente anônimas")
        confissao_embed.timestamp = discord.utils.utcnow()

        log_embed = discord.Embed(
            title="📋 fizeram uma confissão aí",
            description=f"confissão: {confissao_text}",
            color=discord.Color.dark_embed(),
        )
        log_embed.add_field(
            name="👤 enviado por",
            value=f"{interaction.user.mention} (`{interaction.user.id}`)",
            inline=False,
        )
        log_embed.timestamp = discord.utils.utcnow()

        try:
            message = await confissoes_channel.send(
                embed=confissao_embed,
                view=ConfissaoButtonsView(bot),
            )

            confissoes_map[message.id] = {
                "author_id": interaction.user.id,
                "confissao_text": confissao_text,
                "reports": 0,
            }

            await logs_channel.send(embed=log_embed)
            await safe_reply(interaction, "✅ sua confissão foi enviada anonimamente")

        except discord.Forbidden:
            await safe_reply(interaction, "❌ não tenho permissão pra enviar mensagem em algum canal.")
        except Exception as e:
            await safe_reply(interaction, f"❌ erro ao enviar confissão: `{type(e).__name__}: {e}`")


class RespostaConfissaoModal(discord.ui.Modal, title="responder confissão"):
    resposta = discord.ui.TextInput(
        label="sua resposta",
        placeholder="responda com educação e respeito",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=4000,
        required=True,
    )

    def __init__(self, confissao_message_id: int, bot: commands.Bot):
        super().__init__()
        self.confissao_message_id = confissao_message_id
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        confissoes_channel = await get_channel(self.bot, CONFISSOES_CHANNEL_ID)
        if confissoes_channel is None:
            await safe_reply(interaction, "❌ canal de confissões não encontrado.")
            return

        try:
            confissao_msg = await confissoes_channel.fetch_message(self.confissao_message_id)

            resposta_embed = discord.Embed(
                title="💬 resposta à confissão",
                color=discord.Color.dark_embed(),
            )
            resposta_embed.add_field(
                name="respondendo para",
                value=f"[clique aqui]({confissao_msg.jump_url})",
                inline=False,
            )
            resposta_embed.add_field(
                name="resposta",
                value=str(self.resposta.value).strip(),
                inline=False,
            )
            resposta_embed.set_footer(text="resposta anônima")
            resposta_embed.timestamp = discord.utils.utcnow()

            await confissoes_channel.send(
                embed=resposta_embed,
                view=ConfissaoButtonsView(self.bot),
            )
            await safe_reply(interaction, "✅ sua resposta foi enviada!")

        except Exception as e:
            await safe_reply(interaction, f"❌ erro ao enviar resposta: `{type(e).__name__}: {e}`")


class AvisoModal(discord.ui.Modal, title="avisar usuário"):
    motivo = discord.ui.TextInput(
        label="motivo do aviso",
        placeholder="explique o motivo do aviso",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=2000,
        required=True,
    )

    def __init__(self, user_id: int, bot: commands.Bot):
        super().__init__()
        self.user_id = user_id
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await self.bot.fetch_user(self.user_id)
            logs_channel = await get_channel(self.bot, LOGS_CHANNEL_ID)
            confissoes_channel = await get_channel(self.bot, CONFISSOES_CHANNEL_ID)

            aviso_embed = discord.Embed(
                title="⚠️ você recebeu um aviso",
                description=f"**motivo:** {self.motivo.value}",
                color=discord.Color.orange(),
            )
            aviso_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
            aviso_embed.timestamp = discord.utils.utcnow()

            try:
                await user.send(embed=aviso_embed)
                await safe_reply(interaction, f"✅ aviso enviado para {user.mention} via DM")
            except discord.Forbidden:
                if confissoes_channel:
                    await confissoes_channel.send(f"{user.mention}", embed=aviso_embed)
                await safe_reply(interaction, f"⚠️ a DM de {user.mention} estava fechada. Mandei no canal.")

            if logs_channel:
                log_embed = discord.Embed(title="📋 aviso emitido", color=discord.Color.orange())
                log_embed.add_field(name="usuário", value=user.mention, inline=False)
                log_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
                log_embed.add_field(name="motivo", value=self.motivo.value, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                await logs_channel.send(embed=log_embed)

        except Exception as e:
            await safe_reply(interaction, f"❌ erro ao avisar usuário: `{type(e).__name__}: {e}`")


class CastigoModal(discord.ui.Modal, title="castigar usuário"):
    tempo = discord.ui.TextInput(
        label="tempo do castigo",
        placeholder="ex: 1h, 30m, 1d ou 31/12/2026 23:59",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=100,
        required=True,
    )

    motivo = discord.ui.TextInput(
        label="motivo do castigo",
        placeholder="explique o motivo do castigo",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=2000,
        required=True,
    )

    def __init__(self, user_id: int, bot: commands.Bot, guild: discord.Guild):
        super().__init__()
        self.user_id = user_id
        self.bot = bot
        self.guild = guild

    def parse_duration(self, duration_str: str) -> timedelta:
        duration_str = duration_str.strip().lower()

        try:
            if "/" in duration_str or ":" in duration_str:
                dt = datetime.strptime(duration_str, "%d/%m/%Y %H:%M")
                duration = dt - datetime.now()
                if duration.total_seconds() <= 0:
                    raise ValueError("a data precisa estar no futuro")
                return duration
        except ValueError:
            raise
        except Exception:
            pass

        match = re.match(r"^(\d+)([smhd])$", duration_str)
        if not match:
            raise ValueError("formato de duração inválido")

        value = int(match.group(1))
        unit = match.group(2)
        multipliers = {
            "s": timedelta(seconds=value),
            "m": timedelta(minutes=value),
            "h": timedelta(hours=value),
            "d": timedelta(days=value),
        }
        return multipliers[unit]

    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = await self.guild.fetch_member(self.user_id)
            duration = self.parse_duration(str(self.tempo.value))

            await member.timeout(duration, reason=str(self.motivo.value))

            logs_channel = await get_channel(self.bot, LOGS_CHANNEL_ID)
            if logs_channel:
                log_embed = discord.Embed(title="🔇 usuário castigado", color=discord.Color.red())
                log_embed.add_field(name="usuário", value=member.mention, inline=False)
                log_embed.add_field(name="tempo", value=self.tempo.value, inline=False)
                log_embed.add_field(name="motivo", value=self.motivo.value, inline=False)
                log_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                await logs_channel.send(embed=log_embed)

            await safe_reply(interaction, f"✅ {member.mention} foi castigado por {self.tempo.value}")

        except ValueError as e:
            await safe_reply(interaction, f"❌ tempo inválido: {e}. Use `1h`, `30m`, `1d` ou `DD/MM/YYYY HH:MM`.")
        except discord.Forbidden:
            await safe_reply(interaction, "❌ não tenho permissão/cargo alto o suficiente pra castigar esse usuário.")
        except Exception as e:
            await safe_reply(interaction, f"❌ erro ao castigar usuário: `{type(e).__name__}: {e}`")


class ConfissaoButtonsView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Responder", style=discord.ButtonStyle.green, emoji="💬", custom_id="confissao_responder")
    async def responder_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RespostaConfissaoModal(interaction.message.id, self.bot))

    @discord.ui.button(label="Denunciar", style=discord.ButtonStyle.red, emoji="⚠️", custom_id="confissao_denunciar")
    async def denunciar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        message = interaction.message
        dados = confissoes_map.get(message.id)

        reports = 1
        if dados:
            dados["reports"] = dados.get("reports", 0) + 1
            reports = dados["reports"]

        denuncias_channel = await get_channel(self.bot, DENUNCIAS_CHANNEL_ID)
        if denuncias_channel is None:
            await safe_reply(interaction, "❌ canal de denúncias não encontrado")
            return

        denuncia_embed = discord.Embed(
            title="🚨 nova denúncia de confissão",
            description=f"confissão denunciada {reports}x",
            color=discord.Color.red(),
        )
        denuncia_embed.add_field(
            name="confissão",
            value=message.embeds[0].description if message.embeds else "confissão não encontrada",
            inline=False,
        )
        denuncia_embed.add_field(name="denunciado por", value=interaction.user.mention, inline=False)
        denuncia_embed.add_field(name="link da confissão", value=f"[clique aqui]({message.jump_url})", inline=False)
        denuncia_embed.timestamp = discord.utils.utcnow()

        role = interaction.guild.get_role(MODERACAO_ROLE_ID) if interaction.guild else None
        role_mention = role.mention if role else f"<@&{MODERACAO_ROLE_ID}>"

        await denuncias_channel.send(
            f"{role_mention}\nhouve uma denúncia de confissão",
            embed=denuncia_embed,
            view=ModeracaoView(self.bot, message.id),
            allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False),
        )
        await safe_reply(interaction, "✅ denúncia enviada para a moderação.")


class ModeracaoView(discord.ui.View):
    def __init__(self, bot: commands.Bot, confissao_message_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.confissao_message_id = confissao_message_id

    @discord.ui.select(
        placeholder="abrir caso de moderação",
        options=[
            discord.SelectOption(label="Avisar", value="avisar", emoji="⚠️"),
            discord.SelectOption(label="Castigar", value="castigar", emoji="🔇"),
            discord.SelectOption(label="Expulsar", value="expulsar", emoji="👢"),
            discord.SelectOption(label="Banir", value="banir", emoji="🔨"),
        ],
    )
    async def moderacao_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        action = select.values[0]
        dados = confissoes_map.get(self.confissao_message_id)

        if not dados:
            await safe_reply(interaction, "❌ não consegui identificar o autor. Se o bot reiniciou depois da confissão, esse dado foi perdido.")
            return

        user_id = int(dados["author_id"])

        if action in ("avisar", "castigar") and not interaction.user.guild_permissions.moderate_members:
            await safe_reply(interaction, "❌ você não tem permissão para isso.")
            return
        if action == "expulsar" and not interaction.user.guild_permissions.kick_members:
            await safe_reply(interaction, "❌ você não tem permissão para expulsar usuários.")
            return
        if action == "banir" and not interaction.user.guild_permissions.ban_members:
            await safe_reply(interaction, "❌ você não tem permissão para banir usuários.")
            return

        if action == "avisar":
            await interaction.response.send_modal(AvisoModal(user_id, self.bot))
            return

        if action == "castigar":
            await interaction.response.send_modal(CastigoModal(user_id, self.bot, interaction.guild))
            return

        logs_channel = await get_channel(self.bot, LOGS_CHANNEL_ID)

        try:
            if action == "expulsar":
                member = await interaction.guild.fetch_member(user_id)
                await member.kick(reason="confissão inapropriada")
                title = "👢 usuário expulso"
                msg = f"✅ usuário <@{user_id}> foi expulso"

            else:
                user = await self.bot.fetch_user(user_id)
                await interaction.guild.ban(user, reason="confissão inapropriada")
                title = "🔨 usuário banido"
                msg = f"✅ usuário {user.mention} foi banido"

            if logs_channel:
                log_embed = discord.Embed(title=title, color=discord.Color.red())
                log_embed.add_field(name="usuário", value=f"<@{user_id}>", inline=False)
                log_embed.add_field(name="motivo", value="confissão inapropriada", inline=False)
                log_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                await logs_channel.send(embed=log_embed)

            await safe_reply(interaction, msg)

        except discord.Forbidden:
            await safe_reply(interaction, "❌ não tenho permissão/cargo alto o suficiente para fazer isso.")
        except Exception as e:
            await safe_reply(interaction, f"❌ erro na ação de moderação: `{type(e).__name__}: {e}`")


class Confissoes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(ConfissaoButtonsView(self.bot))

    @app_commands.command(name="confissao", description="Envie uma confissão anônima")
    @app_commands.guilds(GUILD)
    async def confissao(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ConfissaoModal())


async def setup(bot: commands.Bot):
    await bot.add_cog(Confissoes(bot))
    print("✅ Cog de confissões carregado.")
