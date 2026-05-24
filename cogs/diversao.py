import discord
import time
import random
from discord.ext import commands
from discord import app_commands

LOGS_CHANNEL_ID = 1490679538559221770
CONFISSOES_CHANNEL_ID = 1507592685282787421
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

async def setup(bot):
    await bot.add_cog(Diversao(bot))
