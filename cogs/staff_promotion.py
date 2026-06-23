import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime

class StaffPromotion(commands.Cog):
    """Sistema de promoção de staffs baseado em pontuação"""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "staff_points.json"
        self.load_data()
        
        # Configuração de cargos e pontos necessários
        self.promotion_chains = {
            1490679537032495301: {
                "next_role": 1490679537032495298,
                "points_needed": 25,
                "role_name": "ೀ Helpers"
            },
            1490679537032495298: {
                "next_role": 1490679537032495302,
                "points_needed": 35,
                "role_name": "ೀ Supervisão"
            },
            1490679537032495302: {
                "next_role": 1518394774414037042,
                "points_needed": 45,
                "role_name": "ೀ Direção"
            },
            1518394774414037042: {
                "next_role": 1490679537032495303,
                "points_needed": 55,
                "role_name": "ೀ Administração"
            },
            1490679537032495303: {
                "next_role": None,
                "points_needed": None,
                "role_name": "Gestão ⋆⭒˚.⋆",
                "is_final": True
            }
        }

    def load_data(self):
        """Carrega os dados de pontos do arquivo JSON"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                self.points_data = json.load(f)
        else:
            self.points_data = {}

    def save_data(self):
        """Salva os dados de pontos no arquivo JSON"""
        with open(self.data_file, 'w') as f:
            json.dump(self.points_data, f, indent=4)

    def get_user_points(self, user_id: int) -> int:
        """Obtém os pontos de um usuário"""
        return self.points_data.get(str(user_id), 0)

    def set_user_points(self, user_id: int, points: int):
        """Define os pontos de um usuário"""
        self.points_data[str(user_id)] = max(0, points)
        self.save_data()

    def add_points(self, user_id: int, amount: int):
        """Adiciona pontos a um usuário"""
        current = self.get_user_points(user_id)
        self.set_user_points(user_id, current + amount)

    def get_highest_staff_role(self, member: discord.Member) -> int:
        """Obtém o cargo staff mais alto do membro"""
        for role in member.roles:
            if role.id in self.promotion_chains:
                return role.id
        return None

    async def check_and_promote(self, member: discord.Member) -> bool:
        """
        Verifica se o membro deve ser promovido e faz a promoção
        Retorna True se foi promovido, False caso contrário
        """
        current_role_id = self.get_highest_staff_role(member)
        
        if current_role_id is None:
            return False

        current_points = self.get_user_points(member.id)
        promotion_info = self.promotion_chains.get(current_role_id)

        # Verifica se é o cargo final (não sobe mais)
        if promotion_info.get("is_final"):
            return False

        points_needed = promotion_info.get("points_needed")

        if current_points >= points_needed:
            next_role_id = promotion_info.get("next_role")
            
            try:
                current_role = member.guild.get_role(current_role_id)
                next_role = member.guild.get_role(next_role_id)
                
                if current_role and next_role:
                    # Remove o cargo antigo e adiciona o novo
                    await member.remove_roles(current_role)
                    await member.add_roles(next_role)
                    
                    # Reseta os pontos para 0 (ou você pode manter)
                    self.set_user_points(member.id, 0)
                    
                    return True
            except Exception as e:
                print(f"Erro ao promover {member}: {e}")
                return False

        return False

    @app_commands.command(
        name="ponto",
        description="Adiciona ou remove pontos de um staff"
    )
    @app_commands.describe(
        staff="O staff que receberá os pontos",
        quantia="Quantidade de pontos (positivo para adicionar, negativo para remover, exemplo: -15, +15)"
    )
    async def add_points_command(
        self,
        interaction: discord.Interaction,
        staff: discord.Member,
        quantia: int
    ):
        """Comando para adicionar/remover pontos manualmente"""
        
        # Verificação de permissões - apenas líderes/admins podem usar
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ você não tem permissão para usar este comando",
                ephemeral=True
            )
            return

        # Verifica se o staff tem cargo staff
        if self.get_highest_staff_role(staff) is None:
            await interaction.response.send_message(
                f"❌ {staff.mention} não possui um cargo de staff",
                ephemeral=True
            )
            return

        # Adiciona/remove os pontos
        self.add_points(staff.id, quantia)
        new_points = self.get_user_points(staff.id)

        # Verifica se deve ser promovido
        was_promoted = await self.check_and_promote(staff)

        if was_promoted:
            current_role = self.get_highest_staff_role(staff)
            role_name = self.promotion_chains[current_role]["role_name"]
            
            embed = discord.Embed(
                title="🎉 promoção de staff!",
                description=f"{staff.mention} foi promovido para **{role_name}**!",
                color=discord.Color.gold()
            )
            embed.add_field(name="pontos Anteriores", value=f"{new_points - quantia}", inline=False)
            embed.add_field(name="pontos Atuais", value="0", inline=False)
            embed.set_thumbnail(url=staff.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="📊 pontos atualizados",
                description=f"pontos de {staff.mention} foram atualizados!",
                color=discord.Color.blue()
            )
            embed.add_field(name="operação", value=f"+{quantia}" if quantia > 0 else f"{quantia}", inline=False)
            embed.add_field(name="pontos totais", value=f"{new_points}", inline=False)
            
            # Mostra progresso para a próxima promoção
            current_role_id = self.get_highest_staff_role(staff)
            if current_role_id:
                promotion_info = self.promotion_chains[current_role_id]
                if not promotion_info.get("is_final"):
                    points_needed = promotion_info["points_needed"]
                    next_role_name = self.promotion_chains[promotion_info["next_role"]]["role_name"]
                    embed.add_field(
                        name="Próxima Promoção",
                        value=f"{next_role_name}: {new_points}/{points_needed} pontos",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="Status",
                        value="⭐ cargo máximo atingido! agora que chegou na gestão do servidor, você só sobe de cargo por mérito da dona(decisão da dona do servidor)",
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="pontos",
        description="Visualiza os pontos de um staff"
    )
    @app_commands.describe(staff="O staff para visualizar pontos (opcional)")
    async def view_points_command(
        self,
        interaction: discord.Interaction,
        staff: discord.Member = None
    ):
        """Comando para visualizar pontos"""
        
        target = staff or interaction.user

        # Verifica se tem cargo staff
        current_role_id = self.get_highest_staff_role(target)
        if current_role_id is None:
            await interaction.response.send_message(
                f"❌ {target.mention} não possui um cargo de staff",
                ephemeral=True
            )
            return

        points = self.get_user_points(target.id)
        promotion_info = self.promotion_chains[current_role_id]
        role_name = promotion_info["role_name"]

        embed = discord.Embed(
            title=f"📊 pontos de {target.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="cargo Atual", value=role_name, inline=False)
        embed.add_field(name="pontos Totais", value=str(points), inline=False)

        if not promotion_info.get("is_final"):
            next_role_name = self.promotion_chains[promotion_info["next_role"]]["role_name"]
            points_needed = promotion_info["points_needed"]
            progress = min(points, points_needed)
            
            embed.add_field(
                name="próxima promoção",
                value=f"{next_role_name}: {progress}/{points_needed} pontos",
                inline=False
            )
            
            # Barra de progresso visual
            bar_length = 10
            filled = int((progress / points_needed) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            embed.add_field(name="progresso", value=f"`{bar}`", inline=False)
        else:
            embed.add_field(
                name="status",
                value="⭐ cargo máximo atingido!",
                inline=False
            )

        embed.set_thumbnail(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="resetar_pontos",
        description="reseta os pontos de um staff"
    )
    @app_commands.describe(staff="o staff que terá seus pontos resetados")
    async def reset_points_command(
        self,
        interaction: discord.Interaction,
        staff: discord.Member
    ):
        """Comando para resetar pontos (apenas admin)"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return

        self.set_user_points(staff.id, 0)

        embed = discord.Embed(
            title="🔄 pontos resetados",
            description=f"os pontos de {staff.mention} foram resetados para 0!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        """Evento quando o bot fica pronto"""
        print(f"✅ Cog StaffPromotion carregado com sucesso!")


async def setup(bot):
    """Função de setup do cog"""
    await bot.add_cog(StaffPromotion(bot))
