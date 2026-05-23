"""
EXEMPLOS PRÁTICOS: Como usar Components V2 no Bot
"""

import discord
from discord.ext import commands
from components import (
    BaseEmbed,
    EmbedType,
    ServerInfoEmbed,
    UserInfoEmbed,
    PingEmbed,
    WarnEmbed,
    ErrorEmbed,
    SuccessEmbed,
)


# ============ EXEMPLO 1: Embed Simples ============
async def exemplo_basico(ctx):
    """Criar uma embed básica"""
    embed = BaseEmbed(
        title="👋 Bem-vindo!",
        description="Este é um exemplo básico",
        embed_type=EmbedType.SUCCESS
    ).build()
    
    await ctx.send(embed=embed)


# ============ EXEMPLO 2: Embed com Campos ============
async def exemplo_com_campos(ctx):
    """Criar embed com vários campos"""
    embed = BaseEmbed(
        title="🎮 Perfil do Jogador",
        description="Informações do seu perfil",
        embed_type=EmbedType.INFO,
        thumbnail_url=ctx.author.display_avatar.url
    )
    
    # Adicionar campos com encadeamento
    embed.add_field("⭐ Nível", "50", inline=True) \
         .add_field("💰 Moedas", "10000", inline=True) \
         .add_field("🏆 Ranking", "#1", inline=True) \
         .add_field("📊 Vitórias", "250", inline=False)
    
    await ctx.send(embed=embed.build())


# ============ EXEMPLO 3: Embed Customizada (classe própria) ============
class RPGPlayerEmbed(BaseEmbed):
    """Embed customizada para perfil de jogador RPG"""
    
    def __init__(
        self,
        player_name: str,
        level: int,
        exp: int,
        health: int,
        avatar_url: str
    ):
        super().__init__(
            title=f"⚔️ {player_name}",
            description="Perfil do Jogador",
            embed_type=EmbedType.INFO,
            thumbnail_url=avatar_url,
            color=discord.Color.gold()
        )
        
        # Adicionar informações do jogador
        self.add_field("📊 Nível", str(level), inline=True)
        self.add_field("✨ EXP", f"{exp}/1000", inline=True)
        self.add_field("❤️ Saúde", f"{health}/100", inline=True)


async def usar_embed_customizada(ctx, member: discord.Member):
    """Usar a embed customizada"""
    embed = RPGPlayerEmbed(
        player_name=member.name,
        level=42,
        exp=750,
        health=85,
        avatar_url=member.display_avatar.url
    ).build()
    
    await ctx.send(embed=embed)


# ============ EXEMPLO 4: Tratamento de Erros ============
async def exemplo_com_erro(ctx):
    """Demonstrar erro e sucesso"""
    try:
        # Simular uma operação que pode falhar
        resultado = 10 / 2
        
        embed = SuccessEmbed(
            "✅ Operação Concluída",
            f"Resultado: {resultado}"
        ).build()
        
    except ZeroDivisionError:
        embed = ErrorEmbed(
            "❌ Divisão por Zero",
            "Não é possível dividir por zero!"
        ).build()
    
    await ctx.send(embed=embed)


# ============ EXEMPLO 5: Usar Embeds Pré-Feitas ============
class ExemplosBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name="exemplo_ping")
    async def exemplo_ping(self, ctx):
        """Usar PingEmbed pré-feita"""
        latency = round(self.bot.latency * 1000)
        embed = PingEmbed(latency).build()
        await ctx.send(embed=embed)
    
    @commands.command(name="exemplo_user")
    async def exemplo_user(self, ctx, member: discord.Member = None):
        """Usar UserInfoEmbed pré-feita"""
        member = member or ctx.author
        embed = UserInfoEmbed(member).build()
        await ctx.send(embed=embed)
    
    @commands.command(name="exemplo_server")
    async def exemplo_server(self, ctx):
        """Usar ServerInfoEmbed pré-feita"""
        embed = ServerInfoEmbed(ctx.guild).build()
        await ctx.send(embed=embed)
    
    @commands.command(name="exemplo_aviso")
    @commands.has_permissions(manage_roles=True)
    async def exemplo_aviso(self, ctx, member: discord.Member, *, razao="Sem motivo"):
        """Usar WarnEmbed"""
        embed = WarnEmbed(member, razao, ctx.author).build()
        await ctx.send(embed=embed)


# ============ EXEMPLO 6: Embed com Cores Customizadas ============
async def exemplo_cores(ctx):
    """Demonstrar diferentes cores"""
    cores_exemplo = [
        ("🟢 Verde", discord.Color.green()),
        ("🔴 Vermelho", discord.Color.red()),
        ("🔵 Azul", discord.Color.blue()),
        ("🟡 Amarelo", discord.Color.yellow()),
        ("🟣 Roxo", discord.Color.purple()),
    ]
    
    for nome, cor in cores_exemplo:
        embed = BaseEmbed(
            title=nome,
            description="Cor customizada",
            color=cor
        ).build()
        await ctx.send(embed=embed)


# ============ EXEMPLO 7: Embed Dinâmica ============
async def criar_embed_ranking(ctx, players: list):
    """Criar uma embed com ranking dinâmico"""
    embed = BaseEmbed(
        title="🏆 Ranking do Servidor",
        description="Top 10 Jogadores",
        embed_type=EmbedType.INFO
    )
    
    # Adicionar campos dinamicamente
    for i, player in enumerate(players[:10], 1):
        emoji_medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
        embed.add_field(
            f"{emoji_medal} #{i}",
            f"{player['nome']} - {player['pontos']} pts",
            inline=False
        )
    
    return embed.build()


# ============ EXEMPLO 8: Múltiplas Embeds em Sequência ============
async def exemplo_multiplas(ctx):
    """Enviar várias embeds seguidas"""
    
    # Embed 1
    embed1 = BaseEmbed("1️⃣ Primeira", "Primeira mensagem", EmbedType.SUCCESS).build()
    await ctx.send(embed=embed1)
    
    # Embed 2
    embed2 = BaseEmbed("2️⃣ Segunda", "Segunda mensagem", EmbedType.WARNING).build()
    await ctx.send(embed=embed2)
    
    # Embed 3
    embed3 = BaseEmbed("3️⃣ Terceira", "Terceira mensagem", EmbedType.ERROR).build()
    await ctx.send(embed=embed3)


# ============ EXEMPLO 9: Embed para Responder a Eventos ============
async def on_member_join(member: discord.Member):
    """Enviar embed quando alguém entra no servidor"""
    embed = BaseEmbed(
        title=f"👋 Bem-vindo, {member.name}!",
        description=f"Você é o membro #{member.guild.member_count}",
        embed_type=EmbedType.SUCCESS,
        thumbnail_url=member.display_avatar.url
    )
    
    embed.add_field("🏠 Servidor", member.guild.name, inline=False)
    
    # Enviar para canal de boas-vindas
    welcome_channel = discord.utils.get(
        member.guild.text_channels,
        name="bem-vindos"
    )
    
    if welcome_channel:
        await welcome_channel.send(embed=embed.build())


# ============ EXEMPLO 10: Padrão Factory (Fábrica de Embeds) ============
class EmbedFactory:
    """Factory para criar embeds padronizadas"""
    
    @staticmethod
    def create_notification(titulo: str, mensagem: str) -> discord.Embed:
        """Cria uma notificação padrão"""
        return BaseEmbed(
            title=f"📢 {titulo}",
            description=mensagem,
            embed_type=EmbedType.INFO
        ).build()
    
    @staticmethod
    def create_success(titulo: str, mensagem: str) -> discord.Embed:
        """Cria uma confirmação de sucesso"""
        return SuccessEmbed(f"✅ {titulo}", mensagem).build()
    
    @staticmethod
    def create_warning(titulo: str, mensagem: str) -> discord.Embed:
        """Cria um aviso"""
        return BaseEmbed(
            title=f"⚠️ {titulo}",
            description=mensagem,
            embed_type=EmbedType.WARNING
        ).build()
    
    @staticmethod
    def create_error(titulo: str, mensagem: str) -> discord.Embed:
        """Cria um erro"""
        return ErrorEmbed(f"❌ {titulo}", mensagem).build()


async def usar_factory(ctx):
    """Usar o EmbedFactory"""
    
    # Notificação
    embed1 = EmbedFactory.create_notification(
        "Nova Atualização",
        "O servidor foi atualizado!"
    )
    await ctx.send(embed=embed1)
    
    # Sucesso
    embed2 = EmbedFactory.create_success(
        "Arquivo Salvo",
        "Seu arquivo foi salvo com sucesso!"
    )
    await ctx.send(embed=embed2)
    
    # Aviso
    embed3 = EmbedFactory.create_warning(
        "Baixo Servidor",
        "A RAM está em 95%!"
    )
    await ctx.send(embed=embed3)


# ============ USAR NO BOT ============
async def setup(bot):
    await bot.add_cog(ExemplosBot(bot))
