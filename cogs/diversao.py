import discord
import time
import random
import json
import os
from discord.ext import commands
from discord import app_commands

LOGS_CHANNEL_ID = 1490679538559221770
CONFISSOES_CHANNEL_ID = 1507592685282787421
TARGET_SERVER_ID = 1490679537019654294
SPECIAL_ROLE_IDS = {
    1490782190064373983,
    1490679537032495295,
    1490679537032495297,
    1490679537019654303,
    1490679537032495299,
    1491090814254841886,
    1496282936331337789,
    1500969290093039626
}
REPUTATION_FILE = "reputation_data.json"
REPUTATION_COOLDOWN_FILE = "reputation_cooldowns.json"
REPUTATION_COOLDOWN_HOURS = 6

cooldowns = {}

class ConfissaoModal(discord.ui.Modal):
    """Modal para enviar confissões anônimas"""
    title = "confissão anônima"
    
    confissao = discord.ui.TextInput(
        label="sua confissão",
        placeholder="escrever uma confissão inadequada pode resultar em uma punição dependendo do que você confessou.",
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
            color=discord.Color.purple()
        )
        
        confissao_embed.set_footer(text="as confissões são totalmente anônimas")
        confissao_embed.timestamp = discord.utils.utcnow()
        
        # Embed para o canal de logs (com quem enviou)
        log_embed = discord.Embed(
            title="📋 fizero uma confissão ai",
            description=f"confissão: {confissao_text}",
            color=discord.Color.greyple()
        )
        log_embed.add_field(
            name="👤 enviado por",
            value=f"{interaction.user.mention} ({interaction.user.id})",
            inline=False
        )
        log_embed.timestamp = discord.utils.utcnow()

        try:
            # Enviar confissão anônima para o canal de confissões
            await confissoes_channel.send(embed=confissao_embed)
            
            # Enviar log para o canal de logs
            await logs_channel.send(embed=log_embed)
            
            # Confirmar ao usuário
            await interaction.response.send_message(
                "✅ sua confissão foi enviada anonimamente!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ erro ao enviar confissão(avisa pro salva): {e}",
                ephemeral=True
            )

class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reputation_data = self.load_reputation_data()
        self.cooldown_data = self.load_cooldown_data()
    
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
    @commands.command(name="tomate")
    async def tomate_prefix(self, ctx):
        """Lança um tomate em uma mensagem aleatória (prefixo)"""
        if ctx.author.id != ctx.guild.owner_id:
            last_used = cooldowns.get(ctx.author.id)

            if last_used:
                remaining = 7200 - (time.time() - last_used)

                if remaining > 0:
                    await ctx.send(
                        f"⏳ espere {int(remaining)} segundos para usar novamente"
                    )
                    return

            cooldowns[ctx.author.id] = time.time()

        messages = [msg async for msg in ctx.channel.history(limit=6)]
        messages = [msg for msg in messages if msg.id != ctx.message.id][:5]

        if messages:
            selected_msg = random.choice(messages)
            try:
                await selected_msg.add_reaction("🍅")
            except Exception:
                pass

        await ctx.send("🍅 tomate lançado!")

    @app_commands.command(name="tomate", description="Lança um tomate em uma mensagem aleatória")
    async def tomate_slash(self, interaction: discord.Interaction):
        """Lança um tomate em uma mensagem aleatória (slash)"""
        if interaction.user.id != interaction.guild.owner_id:
            last_used = cooldowns.get(interaction.user.id)

            if last_used:
                remaining = 7200 - (time.time() - last_used)

                if remaining > 0:
                    await interaction.response.send_message(
                        f"⏳ espere {int(remaining)} segundos para usar novamente",
                        ephemeral=True
                    )
                    return

            cooldowns[interaction.user.id] = time.time()

        # Obter mensagens do canal
        messages = [msg async for msg in interaction.channel.history(limit=6)]
        
        if messages:
            selected_msg = random.choice(messages)
            try:
                await selected_msg.add_reaction("🍅")
            except Exception:
                pass

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
