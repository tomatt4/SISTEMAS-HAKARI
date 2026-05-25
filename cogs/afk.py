import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}  # Dicionário: {user_id: "motivo"}

    # ===== COMANDO AFK =====
    @commands.command(name="afk")
    async def afk_prefix(self, ctx: commands.Context, *, reason: str = "sem motivo informado"):
        """Define seu status como AFK com um motivo (prefixo)"""
        self.afk_users[ctx.author.id] = reason
        
        embed = discord.Embed(
            title="🔴 status AFK ativado",
            description=f"{ctx.author.mention} agora está AFK",
            color=discord.Color.red()
        )
        embed.add_field(name="Motivo", value=reason, inline=False)
        await ctx.send(embed=embed)

    @app_commands.command(name="afk", description="Define seu status como AFK")
    @app_commands.describe(reason="Motivo da sua ausência")
    async def afk_slash(self, interaction: discord.Interaction, reason: Optional[str] = None):
        """Define seu status como AFK com um motivo (slash command)"""
        reason = reason or "sem motivo informado"
        self.afk_users[interaction.user.id] = reason
        
        embed = discord.Embed(
            title="🔴 status AFK ativado",
            description=f"{interaction.user.mention} agora está AFK",
            color=discord.Color.red()
        )
        embed.add_field(name="Motivo", value=reason, inline=False)
        await interaction.response.send_message(embed=embed)

    # ===== COMANDO REMOVER AFK =====
    @commands.command(name="voltei")
    async def back_prefix(self, ctx: commands.Context):
        """Remove seu status de AFK (prefixo)"""
        if ctx.author.id not in self.afk_users:
            return await ctx.send("você não está AFK")
        
        motivo = self.afk_users.pop(ctx.author.id)
        
        embed = discord.Embed(
            title="🟢 status AFK removido",
            description=f"{ctx.author.mention} voltou.",
            color=discord.Color.green()
        )
        embed.add_field(name="Estava AFK por", value=motivo, inline=False)
        await ctx.send(embed=embed)

    @app_commands.command(name="voltei", description="Remove seu status de AFK")
    async def back_slash(self, interaction: discord.Interaction):
        """Remove seu status de AFK (slash command)"""
        if interaction.user.id not in self.afk_users:
            return await interaction.response.send_message("você não está AFK")
        
        motivo = self.afk_users.pop(interaction.user.id)
        
        embed = discord.Embed(
            title="🟢 status AFK removido",
            description=f"{interaction.user.mention} voltou",
            color=discord.Color.green()
        )
        embed.add_field(name="estava AFK por", value=motivo, inline=False)
        await interaction.response.send_message(embed=embed)

    # ===== LISTENER PARA MENÇÕES =====
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Detecta menções a usuários AFK e avisa"""
        if message.author.bot:
            return
        
        # Remover AFK do autor se ele enviar uma mensagem
        if message.author.id in self.afk_users:
            self.afk_users.pop(message.author.id)
        
        afk_mentioned = []
        
        # Verificar se é resposta a mensagem de um usuário AFK
        if message.reference:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                if replied_message.author.id in self.afk_users:
                    afk_mentioned.append((replied_message.author, self.afk_users[replied_message.author.id]))
            except:
                pass
        
        # Verificar se há menções diretas a usuários AFK (ignorar @everyone e @here)
        if message.mentions:
            for mentioned in message.mentions:
                # Ignorar se for everyone ou here
                if mentioned.id == message.guild.id if hasattr(message.guild, 'id') else False:
                    continue
                
                # Verificar se é menção direta (não role mention)
                if mentioned.id in self.afk_users and mentioned not in [user[0] for user in afk_mentioned]:
                    afk_mentioned.append((mentioned, self.afk_users[mentioned.id]))
        
        # Ignorar menções de cargos/roles
        role_mentioned = message.role_mentions
        
        if afk_mentioned:
            embed = discord.Embed(
                title="⏱️ aviso",
                description="esse caba ai ta afk macho/macha",
                color=discord.Color.orange()
            )
            
            await message.reply(embed=embed, mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(AFK(bot))
