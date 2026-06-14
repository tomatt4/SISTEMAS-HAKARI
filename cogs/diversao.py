import discord
import time
import random
import json
import os
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import re

LOGS_CHANNEL_ID = 1490679538559221770
CONFISSOES_CHANNEL_ID = 1507592685282787421
DENUNCIAS_CHANNEL_ID = 1512649166244020306  # Canal de denúncias
TARGET_SERVER_ID = 1490679537019654294
MODERACAO_ROLE_ID = 1513653295061798922 # Cargo mencionado nas denúncias
SPECIAL_ROLE_IDS = {
    1490782190064373983,
    1490679537032495295,
    1490679537032495297,
    1490679537019654303,
    1490679537032495299,
    1491090814254841886,
    1496282936331337789,
    1500969290093039626,
    1513653295061798922
}
REPUTATION_FILE = "reputation_data.json"
REPUTATION_COOLDOWN_FILE = "reputation_cooldowns.json"
REPUTATION_COOLDOWN_HOURS = 6

cooldowns = {}
confissoes_map = {}  # Mapa para armazenar IDs de confissões e seus autores (para logs)

class ConfissaoModal(discord.ui.Modal):
    """Modal para enviar confissões anônimas"""
    title = "confissão anônima"
    
    confissao = discord.ui.TextInput(
        label="sua confissão",
        placeholder="não escreve merda que se não o pior pode vir cara.... não seja teimoso ☠️",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=4000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Obter os canais
        logs_channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
        confissoes_channel = interaction.client.get_channel(CONFISSOES_CHANNEL_ID)
        
        if not logs_channel or not confissoes_channel:
            await interaction.response.send_message(
                "não foi possível enviar sua confissão, avisa isso pro salva",
                ephemeral=True
            )
            return

        # Obter o texto da confissão
        confissao_text = self.confissao.value
        
        # Embed para o canal de confissões (anônimo)
        confissao_embed = discord.Embed(
            title="🔐 nova confissão anônima",
            description=f"confissão: {confissao_text}",
            color=0x0000
        )
        
        confissao_embed.set_footer(text="as confissões são totalmente anônimas")
        confissao_embed.timestamp = discord.utils.utcnow()
        
        # Embed para o canal de logs (com quem enviou)
        log_embed = discord.Embed(
            title="📋 fizeram uma confissão ai",
            description=f"confissão: {confissao_text}",
            color=0x0000
        )
        log_embed.add_field(
            name="👤 enviado por",
            value=f"{interaction.user.mention} ({interaction.user.id})",
            inline=False
        )
        log_embed.timestamp = discord.utils.utcnow()

        try:
            # Enviar confissão anônima para o canal de confissões com view
            message = await confissoes_channel.send(
                embed=confissao_embed,
                view=ConfissaoButtonsView(interaction.client)
            )
            
            # Armazenar o ID da confissão para referência
            confissoes_map[message.id] = {
                "author_id": interaction.user.id,
                "confissao_text": confissao_text,
                "reported": False,
                "reports": 0
            }
            
            # Enviar log para o canal de logs
            await logs_channel.send(embed=log_embed)
            
            # Confirmar ao usuário
            await interaction.response.send_message(
                "✅ sua confissão foi enviada anonimamente",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ erro ao enviar confissão(avisa pro salva): {e}",
                ephemeral=True
            )


class RespostaConfissaoModal(discord.ui.Modal):
    """Modal para responder a uma confissão"""
    title = "responder confissão"
    
    resposta = discord.ui.TextInput(
        label="sua resposta",
        placeholder="responda com educação e respeito",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=4000,
        required=True
    )
    
    def __init__(self, confissao_message_id: int, confissao_text: str, bot):
        super().__init__()
        self.confissao_message_id = confissao_message_id
        self.confissao_text = confissao_text
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        confissoes_channel = interaction.client.get_channel(CONFISSOES_CHANNEL_ID)
        
        if not confissoes_channel:
            await interaction.response.send_message(
                f"❌ erro ao enviar resposta: ``{e}``, COPIA ESSE AVISO E FALA COM O SALVA PELO AMOR DE DEUS",
                ephemeral=True
            )
            return
        
        try:
            # Obter a mensagem original da confissão
            confissao_msg = await confissoes_channel.fetch_message(self.confissao_message_id)
            
            # Criar embed de resposta
            resposta_embed = discord.Embed(
                title="💬 resposta à confissão",
                color=0x0000
            )
            resposta_embed.add_field(
                name="respondendo para",
                value=f"[clique aqui]({confissao_msg.jump_url})",
                inline=False
            )
            resposta_embed.add_field(
                name="resposta",
                value=self.resposta.value,
                inline=False
            )
            resposta_embed.add_field(
                name="destinatário",
                value=interaction.user.mention,
                inline=False
            )
            resposta_embed.set_footer(text="as confissões sempre são- pera aí, a água é azul porque o mar é azul ou é transparente porque a água de um copo é transparente🤔")
            resposta_embed.timestamp = discord.utils.utcnow()
            
            # Enviar a resposta no canal
            await confissoes_channel.send(
                embed=resposta_embed,
                view=ConfissaoButtonsView(interaction.client)
            )
            
            await interaction.response.send_message(
                "✅ sua resposta foi enviada!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ erro ao enviar resposta: {e}",
                ephemeral=True
            )


class AvisoModal(discord.ui.Modal):
    """Modal para avisar um usuário"""
    title = "avisar usuário"
    
    motivo = discord.ui.TextInput(
        label="motivo do aviso",
        placeholder="explique o motivo do aviso",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=2000,
        required=True
    )
    
    def __init__(self, user_id: int, bot, interaction_obj):
        super().__init__()
        self.user_id = user_id
        self.bot = bot
        self.interaction_obj = interaction_obj
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await self.bot.fetch_user(self.user_id)
            logs_channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
            
            aviso_embed = discord.Embed(
                title="⚠️ você recebeu um aviso",
                description=f"**motivo:** {self.motivo.value}",
                color=discord.Color.orange()
            )
            aviso_embed.add_field(
                name="moderador",
                value=interaction.user.mention,
                inline=False
            )
            aviso_embed.timestamp = discord.utils.utcnow()
            
            # Tentar enviar DM
            try:
                await user.send(embed=aviso_embed)
                await interaction.response.send_message(
                    f"✅ aviso enviado para {user.mention} via DM",
                    ephemeral=True
                )
            except discord.Forbidden:
                # Se a DM estiver fechada, enviar no canal público
                confissoes_channel = interaction.client.get_channel(CONFISSOES_CHANNEL_ID)
                await confissoes_channel.send(
                    f"{user.mention}\n",
                    embed=aviso_embed
                )
                await interaction.response.send_message(
                    f"⚠️ DM de {user.mention} estava fechada. Aviso enviado no canal público.",
                    ephemeral=True
                )
            
            # Log da ação
            if logs_channel:
                log_embed = discord.Embed(
                    title="📋 aviso emitido",
                    color=discord.Color.orange()
                )
                log_embed.add_field(name="usuário", value=user.mention, inline=False)
                log_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
                log_embed.add_field(name="motivo", value=self.motivo.value, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                await logs_channel.send(embed=log_embed)
        
        except Exception as e:
            await interaction.response.send_message(
                f"❌ erro ao avisar usuário: {e}",
                ephemeral=True
            )


class CastigoModal(discord.ui.Modal):
    """Modal para castigar um usuário com mute"""
    title = "castigar usuário"
    
    tempo = discord.ui.TextInput(
        label="tempo do castigo",
        placeholder="ex: 1h, 30m, 1d, ou data/hora específica (DD/MM/YYYY HH:MM)",
        style=discord.TextStyle.short,
        min_length=1,
        max_length=100,
        required=True
    )
    
    motivo = discord.ui.TextInput(
        label="motivo do castigo",
        placeholder="explique o motivo do castigo",
        style=discord.TextStyle.paragraph,
        min_length=1,
        max_length=2000,
        required=True
    )
    
    def __init__(self, user_id: int, bot, guild, interaction_obj):
        super().__init__()
        self.user_id = user_id
        self.bot = bot
        self.guild = guild
        self.interaction_obj = interaction_obj
    
    async def parse_duration(self, duration_str: str) -> timedelta:
        """Converte string de duração em timedelta"""
        duration_str = duration_str.strip().lower()
        
        # Verificar se é uma data/hora específica
        try:
            if "/" in duration_str or ":" in duration_str:
                dt = datetime.strptime(duration_str, "%d/%m/%Y %H:%M")
                return dt - datetime.now()
        except:
            pass
        
        # Parsear abreviações
        match = re.match(r'^(\d+)([smhd])$', duration_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit == 's':
                return timedelta(seconds=value)
            elif unit == 'm':
                return timedelta(minutes=value)
            elif unit == 'h':
                return timedelta(hours=value)
            elif unit == 'd':
                return timedelta(days=value)
        
        raise ValueError("Formato de duração inválido")
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            member = await self.guild.fetch_member(self.user_id)
            
            # Parsear duração
            try:
                duration = await self.parse_duration(self.tempo.value)
            except ValueError:
                await interaction.response.send_message(
                    "❌ formato de tempo inválido. use: 1h, 30m, 1d, ou DD/MM/YYYY HH:MM",
                    ephemeral=True
                )
                return
            
            # Aplicar timeout
            try:
                await member.timeout(duration, reason=self.motivo.value)
                
                logs_channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
                log_embed = discord.Embed(
                    title="🔇 usuário castigado (mute)",
                    color=discord.Color.red()
                )
                log_embed.add_field(name="usuário", value=member.mention, inline=False)
                log_embed.add_field(name="tempo", value=self.tempo.value, inline=False)
                log_embed.add_field(name="motivo", value=self.motivo.value, inline=False)
                log_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                
                if logs_channel:
                    await logs_channel.send(embed=log_embed)
                
                await interaction.response.send_message(
                    f"✅ {member.mention} foi castigado por {self.tempo.value}",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    f"❌ sem permissão para castigar {member.mention}",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ erro ao castigar usuário: {e}",
                ephemeral=True
            )


class ConfissaoButtonsView(discord.ui.View):
    """View com botões Responder e Denunciar para confissões"""
    
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="Responder", style=discord.ButtonStyle.green, emoji="💬", custom_id="confissao_responder")
    async def responder_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Obter dados da confissão
        message = interaction.message
        
        # Extrair texto da confissão da embed
        confissao_text = "Confissão"
        if message.embeds:
            embed = message.embeds[0]
            if embed.description:
                confissao_text = embed.description.replace("confissão: ", "")
        
        # Abrir modal de resposta
        modal = RespostaConfissaoModal(message.id, confissao_text, self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Denunciar", style=discord.ButtonStyle.red, emoji="⚠️", custom_id="confissao_denunciar")
    async def denunciar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Incrementar reports
        message = interaction.message
        if message.id in confissoes_map:
            confissoes_map[message.id]["reports"] += 1
            reports = confissoes_map[message.id]["reports"]
        else:
            reports = 1
        
        # Obter canais
        denuncias_channel = interaction.client.get_channel(DENUNCIAS_CHANNEL_ID)
        
        if not denuncias_channel:
            await interaction.response.send_message(
                "❌ canal de denúncias não encontrado",
                ephemeral=True
            )
            return
        
        # Criar embed de denúncia
        denuncia_embed = discord.Embed(
            title="🚨 nova denúncia de confissão",
            description=f"confissão denunciada {reports}x",
            color=discord.Color.red()
        )
        denuncia_embed.add_field(
            name="confissão",
            value=message.embeds[0].description if message.embeds else "confissão não encontrada",
            inline=False
        )
        denuncia_embed.add_field(
            name="denunciado por",
            value=interaction.user.mention,
            inline=False
        )
        denuncia_embed.add_field(
            name="link da confissão",
            value=f"[clique aqui]({message.jump_url})",
            inline=False
        )
        denuncia_embed.timestamp = discord.utils.utcnow()
        
        # Mencionar cargo de moderação
        role = interaction.guild.get_role(MODERACAO_ROLE_ID)
        role_mention = role.mention if role else f"<@&{MODERACAO_ROLE_ID}>"
        
        # Enviar denúncia
        denuncia_msg = await denuncias_channel.send(
            f"{role_mention}\n houve uma denúncia de confissão",
            embed=denuncia_embed,
            view=ModeracaoView(interaction.client, message.id)
        )
        
        await interaction.response.send_message(
            "✅ denúncia enviada para a moderação",
            ephemeral=True
        )


class ModeracaoView(discord.ui.View):
    """View com select menu para ações de moderação"""
    
    def __init__(self, bot, confissao_message_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.confissao_message_id = confissao_message_id
    
    @discord.ui.select(
        placeholder="abrir caso de moderação",
        custom_id="moderacao_actions",
        options=[
            discord.SelectOption(label="Avisar", value="avisar", emoji="⚠️"),
            discord.SelectOption(label="Castigar", value="castigar", emoji="🔇"),
            discord.SelectOption(label="Expulsar", value="expulsar", emoji="👢"),
            discord.SelectOption(label="Banir", value="banir", emoji="🔨"),
        ]
    )
    async def moderacao_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        action = select.values[0]
        
        # Obter dados da confissão
        confissoes_channel = interaction.client.get_channel(CONFISSOES_CHANNEL_ID)
        
        try:
            confissao_msg = await confissoes_channel.fetch_message(self.confissao_message_id)
        except:
            await interaction.response.send_message(
                "❌ confissão não encontrada",
                ephemeral=True
            )
            return
        
        # Obter o autor da confissão
        if self.confissao_message_id not in confissoes_map:
            await interaction.response.send_message(
                "❌ não foi possível identificar o autor da confissão",
                ephemeral=True
            )
            return
        
        user_id = confissoes_map[self.confissao_message_id]["author_id"]
        
        # Verificar permissões do moderador
        if action == "avisar":
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ você não tem permissão para avisar usuários",
                    ephemeral=True
                )
                return
            
            modal = AvisoModal(user_id, self.bot, interaction)
            await interaction.response.send_modal(modal)
        
        elif action == "castigar":
            if not interaction.user.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    "❌ você não tem permissão para castigar usuários",
                    ephemeral=True
                )
                return
            
            modal = CastigoModal(user_id, self.bot, interaction.guild, interaction)
            await interaction.response.send_modal(modal)
        
        elif action == "expulsar":
            if not interaction.user.guild_permissions.kick_members:
                await interaction.response.send_message(
                    "❌ você não tem permissão para expulsar usuários",
                    ephemeral=True
                )
                return
            
            try:
                member = await interaction.guild.fetch_member(user_id)
                await member.kick(reason="confissão inapropriada")
                
                logs_channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
                log_embed = discord.Embed(
                    title="👢 usuário expulso",
                    color=discord.Color.red()
                )
                log_embed.add_field(name="usuário", value=f"<@{user_id}>", inline=False)
                log_embed.add_field(name="motivo", value="confissão inapropriada", inline=False)
                log_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                
                if logs_channel:
                    await logs_channel.send(embed=log_embed)
                
                await interaction.response.send_message(
                    f"✅ usuário <@{user_id}> foi expulso",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ erro ao expulsar usuário: {e}",
                    ephemeral=True
                )
        
        elif action == "banir":
            if not interaction.user.guild_permissions.ban_members:
                await interaction.response.send_message(
                    "❌ você não tem permissão para banir usuários",
                    ephemeral=True
                )
                return
            
            try:
                user = await self.bot.fetch_user(user_id)
                await interaction.guild.ban(user, reason="confissão inapropriada")
                
                logs_channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
                log_embed = discord.Embed(
                    title="🔨 usuário banido",
                    color=discord.Color.red()
                )
                log_embed.add_field(name="usuário", value=user.mention, inline=False)
                log_embed.add_field(name="motivo", value="confissão inapropriada", inline=False)
                log_embed.add_field(name="moderador", value=interaction.user.mention, inline=False)
                log_embed.timestamp = discord.utils.utcnow()
                
                if logs_channel:
                    await logs_channel.send(embed=log_embed)
                
                await interaction.response.send_message(
                    f"✅ usuário {user.mention} foi banido",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ erro ao banir usuário: {e}",
                    ephemeral=True
                )



class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reputation_data = self.load_reputation_data()
        self.cooldown_data = self.load_cooldown_data()
        # Restaurar views persistentes
        bot.add_view(ConfissaoButtonsView(bot))
        bot.add_view(ModeracaoView(bot, 0))
    
    def load_reputation_data(self):
        """Carrega os dados de reputação do arquivo JSON"""
        if os.path.exists(REPUTATION_FILE):
            try:
                with open(REPUTATION_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erro ao carregar reputação: {e}")
                return {}
        return {}
    
    def save_reputation_data(self):
        """Salva os dados de reputação no arquivo JSON"""
        try:
            with open(REPUTATION_FILE, 'w') as f:
                json.dump(self.reputation_data, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar reputação: {e}")
    
    def load_cooldown_data(self):
        """Carrega os dados de cooldown do arquivo JSON"""
        if os.path.exists(REPUTATION_COOLDOWN_FILE):
            try:
                with open(REPUTATION_COOLDOWN_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erro ao carregar cooldowns: {e}")
                return {}
        return {}
    
    def save_cooldown_data(self):
        """Salva os dados de cooldown no arquivo JSON"""
        try:
            with open(REPUTATION_COOLDOWN_FILE, 'w') as f:
                json.dump(self.cooldown_data, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar cooldowns: {e}")
    
    def get_cooldown_remaining(self, user_id: int, server_id: int) -> int:
        """Retorna os segundos restantes de cooldown (0 se disponível)"""
        key = f"{server_id}:{user_id}"
        last_time = self.cooldown_data.get(key, 0)
        cooldown_seconds = REPUTATION_COOLDOWN_HOURS * 3600
        remaining = cooldown_seconds - (time.time() - last_time)
        return max(0, int(remaining))
    
    def set_cooldown(self, user_id: int, server_id: int):
        """Define o cooldown para um usuário"""
        key = f"{server_id}:{user_id}"
        self.cooldown_data[key] = time.time()
        self.save_cooldown_data()
    
    def is_on_cooldown(self, user_id: int, server_id: int) -> bool:
        """Verifica se o usuário está em cooldown"""
        return self.get_cooldown_remaining(user_id, server_id) > 0
    
    def get_user_reputation(self, user_id: int, server_id: int) -> int:
        """Obtém a reputação de um usuário em um servidor específico"""
        key = f"{server_id}:{user_id}"
        return self.reputation_data.get(key, 0)
    
    def add_reputation(self, user_id: int, server_id: int, amount: int):
        """Adiciona reputação a um usuário"""
        key = f"{server_id}:{user_id}"
        self.reputation_data[key] = self.get_user_reputation(user_id, server_id) + amount
        self.save_reputation_data()
    
    def get_top_users(self, server_id: int, limit: int = 10) -> list:
        """Obtém os top usuários com mais reputação no servidor"""
        server_users = {}
        for key, rep in self.reputation_data.items():
            parts = key.split(":")
            if len(parts) == 2 and parts[0] == str(server_id):
                user_id = int(parts[1])
                server_users[user_id] = rep
        
        # Ordena por reputação (descendente) e retorna os top N
        sorted_users = sorted(server_users.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]
    
    def has_special_role(self, member: discord.Member) -> bool:
        """Verifica se o membro tem um dos cargos especiais"""
        for role in member.roles:
            if role.id in SPECIAL_ROLE_IDS:
                return True
        return False

    # ===== COMANDO TOMATE =====
    @app_commands.command(name="tomate", description="Lança um tomate em uma mensagem aleatória")
    async def tomate_slash(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            last_used = cooldowns.get(interaction.user.id)

            if last_used:
                remaining = 1800 - (time.time() - last_used)

            if remaining > 0:
                await interaction.response.send_message(
                    f"⏳ espere {int(remaining)} segundos para usar novamente",
                    ephemeral=True
                )
                return

                    cooldowns[interaction.user.id] = time.time()

    channel = interaction.channel

    messages = [
        msg async for msg in channel.history(limit=10)
        if not msg.author.bot
    ]

    if not messages:
        await interaction.response.send_message("🍅 não achei mensagem pra tacar tomate.")
        return
        
    selected_msg = random.choice(messages)

    try:
        await selected_msg.add_reaction("🍅")
    except discord.Forbidden:
        await interaction.response.send_message("❌ não tenho permissão pra reagir mensagens.")
        return
    except Exception as e:
        await interaction.response.send_message(f"❌ erro ao lançar tomate: `{e}`")
        return

    await interaction.response.send_message("🍅 tomate lançado!")
    
    # ===== COMANDO CONFISSÃO =====
    @app_commands.command(name="confissao", description="Envie uma confissão anônima")
    async def confissao(self, interaction: discord.Interaction):
        """Abre modal para confissão anônima (slash only)"""
        await interaction.response.send_modal(ConfissaoModal())

    # ===== SISTEMA DE REPUTAÇÃO =====
    
    @commands.command(name="rep")
    async def rep_prefix(self, ctx, *, args=None):
        """Comandos de reputação (prefixo)
        Uso: ,rep <usuario> | ,rep quantidade | ,rankrep
        """
        if not args:
            await ctx.send("❌ use: `,rep <usuario>`, `,rep quantidade` ou `,rankrep`")
            return
        
        args = args.strip().split()
        
        # Comando: ,rep quantidade
        if args[0].lower() == "quantidade":
            rep = self.get_user_reputation(ctx.author.id, ctx.guild.id)
            embed = discord.Embed(
                title=f"📊 reputação de {ctx.author.name}",
                description=f"você tem **{rep}** de reputação",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return
        
        # Comando: ,rankrep
        if args[0].lower() == "rankrep":
            await self.show_reputation_ranking(ctx, ctx.guild.id)
            return
        
        # Comando: ,rep <usuario>
        if len(ctx.message.mentions) == 0:
            await ctx.send("❌ mencione um usuário para dar reputação")
            return
        
        target_user = ctx.message.mentions[0]
        
        if target_user.id == ctx.author.id:
            await ctx.send("❌ você não pode dar reputação para si mesmo")
            return
        
        # Verifica se está em cooldown
        if self.is_on_cooldown(ctx.author.id, ctx.guild.id):
            remaining = self.get_cooldown_remaining(ctx.author.id, ctx.guild.id)
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            await ctx.send(
                f"⏳ você precisa esperar **{hours}h {minutes}m {seconds}s** para dar reputação novamente"
            )
            return
        
        # Verifica se tem cargo especial
        rep_amount = 2 if self.has_special_role(ctx.author) else 1
        
        self.add_reputation(target_user.id, ctx.guild.id, rep_amount)
        self.set_cooldown(ctx.author.id, ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ reputação adicionada",
            description=f"{ctx.author.mention} deu **{rep_amount}** de reputação para {target_user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="total de reputação",
            value=str(self.get_user_reputation(target_user.id, ctx.guild.id)),
            inline=False
        )
        embed.add_field(
            name="próximo uso em",
            value=f"{REPUTATION_COOLDOWN_HOURS} horas",
            inline=False
        )
        await ctx.send(embed=embed)
    
    @app_commands.command(name="rep", description="Sistema de reputação")
    @app_commands.describe(
        subcommand="ação: dar, quantidade ou rank",
        usuario="usuário para dar reputação"
    )
    async def rep_slash(
        self, 
        interaction: discord.Interaction, 
        subcommand: str,
        usuario: discord.User = None
    ):
        """Comandos de reputação (slash)"""
        subcommand = subcommand.lower()
        
        # Comando: /rep quantidade
        if subcommand == "quantidade":
            rep = self.get_user_reputation(interaction.user.id, interaction.guild.id)
            embed = discord.Embed(
                title=f"📊 reputação de {interaction.user.name}",
                description=f"você tem **{rep}** reputações",
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Comando: /rep rank
        if subcommand == "rank":
            await self.show_reputation_ranking_slash(interaction, interaction.guild.id)
            return
        
        # Comando: /rep dar <usuario>
        if subcommand == "dar":
            if not usuario:
                await interaction.response.send_message(
                    "❌ você precisa mencionar um usuário",
                    ephemeral=True
                )
                return
            
            if usuario.id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ você não pode dar reputação para si mesmo",
                    ephemeral=True
                )
                return
            
            # Verifica se está em cooldown
            if self.is_on_cooldown(interaction.user.id, interaction.guild.id):
                remaining = self.get_cooldown_remaining(interaction.user.id, interaction.guild.id)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                await interaction.response.send_message(
                    f"⏳ você precisa esperar **{hours}h {minutes}m {seconds}s** para dar reputação novamente",
                    ephemeral=True
                )
                return
            
            # Pega o membro para verificar os cargos
            try:
                member = await interaction.guild.fetch_member(interaction.user.id)
            except:
                member = interaction.user
            
            # Verifica se tem cargo especial
            rep_amount = 2 if self.has_special_role(member) else 1
            
            self.add_reputation(usuario.id, interaction.guild.id, rep_amount)
            self.set_cooldown(interaction.user.id, interaction.guild.id)
            
            embed = discord.Embed(
                title="✅ reputação adicionada",
                description=f"{interaction.user.mention} deu **{rep_amount}** de reputação para {usuario.mention}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="total de reputação",
                value=str(self.get_user_reputation(usuario.id, interaction.guild.id)),
                inline=False
            )
            embed.add_field(
                name="próximo uso em",
                value=f"{REPUTATION_COOLDOWN_HOURS} horas",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
            return
        
        await interaction.response.send_message(
            "❌ use: `/rep dar <usuario>`, `/rep quantidade` ou `/rep rank`",
            ephemeral=True
        )
    
    @commands.command(name="rankrep")
    async def rankrep_prefix(self, ctx):
        """Exibe o top 10 de reputação (prefixo)"""
        await self.show_reputation_ranking(ctx, ctx.guild.id)
    
    @commands.command(name="reps")
    async def reps_prefix(self, ctx):
        """Mostra sua reputação atual (prefixo)"""
        rep = self.get_user_reputation(ctx.author.id, ctx.guild.id)
        embed = discord.Embed(
            title=f"📊 reputação de {ctx.author.name}",
            description=f"você tem **{rep}** de reputação",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    async def show_reputation_ranking(self, ctx, server_id: int):
        """Exibe o ranking de reputação no servidor (comando prefix)"""
        top_users = self.get_top_users(server_id, 10)
        
        if not top_users:
            await ctx.send("❌ ninguém tem reputação ainda")
            return
        
        ranking_text = ""
        for i, (user_id, rep) in enumerate(top_users, 1):
            try:
                user = await self.bot.fetch_user(user_id)
                ranking_text += f"{i}. **{user.mention}** - {rep} reputação\n"
            except:
                ranking_text += f"{i}. Usuário #{user_id} - {rep} reputação\n"
        
        embed = discord.Embed(
            title="🏆 top 10 - ranking de reputação",
            description=ranking_text,
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
    
    async def show_reputation_ranking_slash(self, interaction: discord.Interaction, server_id: int):
        """Exibe o ranking de reputação no servidor (comando slash)"""
        top_users = self.get_top_users(server_id, 10)
        
        if not top_users:
            await interaction.response.send_message("❌ ninguém tem reputação ainda")
            return
        
        ranking_text = ""
        for i, (user_id, rep) in enumerate(top_users, 1):
            try:
                user = await self.bot.fetch_user(user_id)
                ranking_text += f"{i}. **{user.mention}** - {rep} reputação\n"
            except:
                ranking_text += f"{i}. usuário #{user_id} - {rep} reputação\n"
        
        embed = discord.Embed(
            title="🏆 top 10 - ranking de reputação",
            description=ranking_text,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Servidor: {interaction.guild.name}")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Diversao(bot))
