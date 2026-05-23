"""
Sistema de Embeds V2 - Componentes modernos e reutilizáveis do Discord
Centraliza toda a criação de embeds com suporte a componentes interativos
"""

import discord
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum


class EmbedType(Enum):
    """Tipos de embeds disponíveis"""
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    NEUTRAL = "neutral"


@dataclass
class EmbedField:
    """Representação de um campo de embed"""
    name: str
    value: str
    inline: bool = True


class BaseEmbed:
    """Classe base para criar embeds de forma simples e reutilizável"""
    
    def __init__(
        self,
        title: str,
        description: str = "",
        embed_type: EmbedType = EmbedType.INFO,
        color: Optional[discord.Color] = None,
        thumbnail_url: Optional[str] = None,
        image_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        footer_icon: Optional[str] = None,
        author_name: Optional[str] = None,
        author_icon: Optional[str] = None,
    ):
        """
        Inicializa uma embed base
        
        Args:
            title: Título da embed
            description: Descrição/conteúdo principal
            embed_type: Tipo de embed (afeta a cor)
            color: Cor customizada (sobrescreve o tipo)
            thumbnail_url: URL da imagem thumbnail
            image_url: URL da imagem grande
            footer_text: Texto do rodapé
            footer_icon: Ícone do rodapé
            author_name: Nome do autor
            author_icon: Ícone do autor
        """
        self.title = title
        self.description = description
        self.embed_type = embed_type
        self.fields: List[EmbedField] = []
        
        # Definir cor baseado no tipo
        if color:
            self.color = color
        else:
            self.color = self._get_color_by_type(embed_type)
        
        self.thumbnail_url = thumbnail_url
        self.image_url = image_url
        self.footer_text = footer_text
        self.footer_icon = footer_icon
        self.author_name = author_name
        self.author_icon = author_icon
    
    @staticmethod
    def _get_color_by_type(embed_type: EmbedType) -> discord.Color:
        """Retorna a cor baseada no tipo de embed"""
        colors = {
            EmbedType.SUCCESS: discord.Color.green(),
            EmbedType.ERROR: discord.Color.red(),
            EmbedType.INFO: discord.Color.blue(),
            EmbedType.WARNING: discord.Color.orange(),
            EmbedType.NEUTRAL: discord.Color.greyple(),
        }
        return colors.get(embed_type, discord.Color.blurple())
    
    def add_field(self, name: str, value: str, inline: bool = True) -> "BaseEmbed":
        """
        Adiciona um campo à embed (permite encadeamento)
        
        Args:
            name: Nome do campo
            value: Valor do campo
            inline: Se o campo deve estar inline
            
        Returns:
            Self para encadeamento
        """
        self.fields.append(EmbedField(name, value, inline))
        return self
    
    def add_fields(self, fields: List[EmbedField]) -> "BaseEmbed":
        """Adiciona múltiplos campos de uma vez"""
        self.fields.extend(fields)
        return self
    
    def build(self) -> discord.Embed:
        """Constrói e retorna a embed discord.Embed pronta para enviar"""
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            color=self.color
        )
        
        # Adicionar campos
        for field in self.fields:
            embed.add_field(
                name=field.name,
                value=field.value,
                inline=field.inline
            )
        
        # Adicionar thumbnail
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)
        
        # Adicionar imagem
        if self.image_url:
            embed.set_image(url=self.image_url)
        
        # Adicionar footer
        if self.footer_text:
            embed.set_footer(
                text=self.footer_text,
                icon_url=self.footer_icon
            )
        
        # Adicionar autor
        if self.author_name:
            embed.set_author(
                name=self.author_name,
                icon_url=self.author_icon
            )
        
        # Adicionar timestamp
        embed.timestamp = discord.utils.utcnow()
        
        return embed


# ============= EMBEDS ESPECÍFICAS DO BOT =============

class ServerInfoEmbed(BaseEmbed):
    """Embed para informações do servidor"""
    
    def __init__(self, guild: discord.Guild):
        super().__init__(
            title=f"🏰 {guild.name}",
            description=f"Informações do servidor {guild.name}",
            embed_type=EmbedType.INFO,
            color=discord.Color.orange(),
            thumbnail_url=guild.icon.url if guild.icon else None,
            image_url=guild.banner.url if guild.banner else None,
        )
        
        self.add_field("👑 Dono", str(guild.owner), inline=False)
        self.add_field("👥 Membros", str(guild.member_count), inline=True)
        self.add_field("🚀 Boosts", str(guild.premium_subscription_count), inline=True)
        self.add_field("⭐ Nível Boost", str(guild.premium_tier), inline=True)
        self.add_field("📆 Criado em", guild.created_at.strftime("%d/%m/%Y"), inline=False)


class UserInfoEmbed(BaseEmbed):
    """Embed para informações de usuário"""
    
    def __init__(self, member: discord.Member):
        super().__init__(
            title=f"👤 Informações de {member}",
            description=f"Perfil de {member.mention}",
            embed_type=EmbedType.INFO,
            color=discord.Color.blue(),
            thumbnail_url=member.display_avatar.url,
        )
        
        self.add_field("🆔 ID", str(member.id), inline=False)
        self.add_field("📅 Conta criada", member.created_at.strftime("%d/%m/%Y"), inline=True)
        self.add_field("📥 Entrou no servidor", member.joined_at.strftime("%d/%m/%Y"), inline=True)
        self.add_field("🤖 Bot?", str(member.bot), inline=True)


class PingEmbed(BaseEmbed):
    """Embed para comando de ping"""
    
    def __init__(self, latency_ms: int):
        # Determinar tipo baseado na latência
        if latency_ms < 100:
            embed_type = EmbedType.SUCCESS
        elif latency_ms < 200:
            embed_type = EmbedType.WARNING
        else:
            embed_type = EmbedType.ERROR
        
        super().__init__(
            title="🏓 Pong!",
            description=f"Latência da API: **{latency_ms}ms** | Ligado 24/7 com **Render** e **UptimeRobot**",
            embed_type=embed_type,
        )


class HelpEmbed(BaseEmbed):
    """Embed para comando de ajuda"""
    
    def __init__(self, bot_name: str, prefix: str, commands_text: str):
        super().__init__(
            title="📚 Ajuda do Bot",
            description="Comandos e informações do bot",
            embed_type=EmbedType.INFO,
            color=discord.Color.blurple(),
        )
        
        self.add_field(
            name="🤖 Informações",
            value=f"**Nome:** {bot_name}\n**Prefixo:** `{prefix}`\n**Suporta:** `/` (slash commands)",
            inline=False
        )
        
        if commands_text:
            self.add_field(
                name="📋 Comandos de Prefixo",
                value=commands_text,
                inline=False
            )
        
        self.add_field(
            name="💡 Dica",
            value="Use `/` para ver todos os slash commands disponíveis!",
            inline=False
        )


class WarnEmbed(BaseEmbed):
    """Embed para aviso de usuário"""
    
    def __init__(self, member: discord.Member, reason: str, moderator: discord.Member):
        super().__init__(
            title="⚠️ Aviso",
            description=f"{member.mention} foi avisado.",
            embed_type=EmbedType.WARNING,
            footer_text=f"Aviso por {moderator}",
            footer_icon=moderator.display_avatar.url,
        )
        
        self.add_field("Motivo", reason, inline=False)
        self.add_field("👤 Membro", str(member), inline=True)


class ConfessionEmbed(BaseEmbed):
    """Embed para confissão anônima"""
    
    def __init__(self, confession_text: str):
        super().__init__(
            title="🔐 Confissão Anônima",
            description=confession_text,
            embed_type=EmbedType.NEUTRAL,
            color=discord.Color.purple(),
            footer_text="Confissão anônima",
        )


class ConfessionLogEmbed(BaseEmbed):
    """Embed para log de confissão"""
    
    def __init__(self, confession_text: str, user: discord.User, guild: discord.Guild):
        super().__init__(
            title="📋 Log de Confissão",
            description=confession_text,
            embed_type=EmbedType.NEUTRAL,
            color=discord.Color.greyple(),
            footer_text=f"Guild: {guild.name}",
        )
        
        self.add_field(
            "👤 Enviado por",
            f"{user.mention} ({user.id})",
            inline=False
        )


class TicketEmbed(BaseEmbed):
    """Embed para painel de tickets"""
    
    def __init__(self, image_url: str = ""):
        super().__init__(
            title="🎫 Sistema de Tickets",
            description="Clique no botão abaixo para abrir um ticket e descrever seu problema.",
            embed_type=EmbedType.INFO,
            color=discord.Color.blurple(),
            image_url=image_url if image_url else None,
        )
        
        self.add_field(
            name="ℹ️ Como funciona",
            value="1. Clique em 'Abrir Ticket'\n2. Descreva seu problema\n3. Aguarde a resposta da equipe",
            inline=False
        )


class TicketOpenedEmbed(BaseEmbed):
    """Embed quando um ticket é aberto"""
    
    def __init__(self, user: discord.Member):
        super().__init__(
            title="🎫 Ticket Aberto",
            description="Explique seu problema e aguarde a equipe de suporte.",
            embed_type=EmbedType.SUCCESS,
        )
        
        self.add_field(
            name="👤 Solicitante",
            value=user.mention,
            inline=False
        )


class ConfirmCloseTicketEmbed(BaseEmbed):
    """Embed para confirmação de fechamento de ticket"""
    
    def __init__(self):
        super().__init__(
            title="⚠️ Confirmação de Fechamento",
            description="Tem certeza que deseja fechar este ticket?",
            embed_type=EmbedType.WARNING,
        )


class TicketClosedEmbed(BaseEmbed):
    """Embed quando ticket é fechado"""
    
    def __init__(self):
        super().__init__(
            title="❌ Ticket Fechado",
            description="O ticket não será fechado.",
            embed_type=EmbedType.ERROR,
        )


class ErrorEmbed(BaseEmbed):
    """Embed genérica de erro"""
    
    def __init__(self, title: str, description: str):
        super().__init__(
            title=title,
            description=description,
            embed_type=EmbedType.ERROR,
        )


class SuccessEmbed(BaseEmbed):
    """Embed genérica de sucesso"""
    
    def __init__(self, title: str, description: str):
        super().__init__(
            title=title,
            description=description,
            embed_type=EmbedType.SUCCESS,
        )
