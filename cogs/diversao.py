import discord
import time
import random
from discord.ext import commands
from discord import app_commands

LOGS_CHANNEL_ID = 1490679538559221770
CONFISSOES_CHANNEL_ID = 1507592685282787421
cooldowns = {}

class ConfissaoModal(discord.ui.Modal, title="Confissão Anônima"):
    """Modal para enviar confissões anônimas"""
    confissao = discord.ui.TextInput(
        label="Sua Confissão",
        placeholder="Escreva sua confissão aqui...",
        style=discord.TextStyle.paragraph,
        min_length=3,
        max_length=4000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Obter os canais
        logs_channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
        confissoes_channel = interaction.client.get_channel(CONFISSOES_CHANNEL_ID)
        
        if not logs_channel or not confissoes_channel:
            await interaction.response.send_message(
                "❌ Não foi possível enviar sua confissão. Canais não encontrados.",
                ephemeral=True
            )
            return

        # Obter o texto da confissão
        confissao_text = self.confissao.value
        
        # Embed para o canal de confissões (anônimo)
        confissao_embed = discord.Embed(
            title="🔐 Confissão Anônima",
            description=confissao_text,
            color=discord.Color.purple()
        )
        confissao_embed.set_footer(text="Confissão anônima")
        confissao_embed.timestamp = discord.utils.utcnow()
        
        # Embed para o canal de logs (com quem enviou)
        log_embed = discord.Embed(
            title="📋 Log de Confissão",
            description=confissao_text,
            color=discord.Color.greyple()
        )
        log_embed.add_field(
            name="👤 Enviado por",
            value=f"{interaction.user.mention} ({interaction.user.id})",
            inline=False
        )
        log_embed.set_footer(text=f"Guild: {interaction.guild.name}")
        log_embed.timestamp = discord.utils.utcnow()

        try:
            # Enviar confissão anônima para o canal de confissões
            await confissoes_channel.send(embed=confissao_embed)
            
            # Enviar log para o canal de logs
            await logs_channel.send(embed=log_embed)
            
            # Confirmar ao usuário
            await interaction.response.send_message(
                "✅ Sua confissão foi enviada anonimamente!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao enviar confissão: {e}",
                ephemeral=True
            )

class Diversao(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ===== COMANDO TOMATE =====
    @commands.command(name="tomate")
    async def tomate_prefix(self, ctx):
        """Lança um tomate em uma mensagem aleatória (prefixo)"""
        if not ctx.author.guild_permissions.administrator:
            last_used = cooldowns.get(ctx.author.id)

            if last_used:
                remaining = 1200 - (time.time() - last_used)

                if remaining > 0:
                    await ctx.send(
                        f"⏳ Espere {int(remaining)} segundos para usar novamente."
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

        await ctx.send("🍅 Tomate lançado!")

    @app_commands.command(name="tomate", description="Lança um tomate em uma mensagem aleatória")
    async def tomate_slash(self, interaction: discord.Interaction):
        """Lança um tomate em uma mensagem aleatória (slash)"""
        if not interaction.user.guild_permissions.administrator:
            last_used = cooldowns.get(interaction.user.id)

            if last_used:
                remaining = 1200 - (time.time() - last_used)

                if remaining > 0:
                    await interaction.response.send_message(
                        f"⏳ Espere {int(remaining)} segundos para usar novamente.",
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

        await interaction.response.send_message("🍅 O tomate foi lançado.")

    # ===== COMANDO CONFISSÃO =====
    @app_commands.command(name="confissao", description="Envie uma confissão anônima")
    async def confissao(self, interaction: discord.Interaction):
        """Abre modal para confissão anônima (slash only)"""
        await interaction.response.send_modal(ConfissaoModal())

async def setup(bot):
    await bot.add_cog(Diversao(bot))
