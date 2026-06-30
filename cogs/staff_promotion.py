import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CARGO_STAFF = 1500969290093039626
CARGO_SECRETARIA = 1513653295061798922


class StaffPromotion(commands.Cog):
    """Sistema de promoção de staffs baseado em pontuação"""

    def __init__(self, bot):
        self.bot = bot
        self.data_file = "staff_points.json"
        self.load_data()

        self.promotion_chains = {
            1490679537032495301: {
                "next_role": 1519102905112858757,
                "points_needed": 10,
                "role_name": "Staff"
            },
            1519102905112858757: {
                "next_role": 1490679537032495298,
                "points_needed": 20,
                "role_name": "Moderador"
            },
            1490679537032495298: {
                "next_role": 1519102475246899341,
                "points_needed": 30,
                "role_name": "Supervisor"
            },
            1519102475246899341: {
                "next_role": 1518394774414037042,
                "points_needed": 40,
                "role_name": "Diretor"
            },
            1518394774414037042: {
                "next_role": 1490679537032495303,
                "points_needed": 50,
                "role_name": "Administrador"
            },
            1490679537032495303: {
                "next_role": 1496282936331337789,
                "points_needed": 60,
                "role_name": "Gestor"
            },
            1496282936331337789: {
                "next_role": None,
                "points_needed": 70,
                "role_name": "Sub Owner",
                "is_final": True
            }
        }

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r") as f:
                self.points_data = json.load(f)
        else:
            self.points_data = {}

    def save_data(self):
        with open(self.data_file, "w") as f:
            json.dump(self.points_data, f, indent=4)

    def get_user_points(self, user_id: int) -> int:
        return self.points_data.get(str(user_id), 0)

    def set_user_points(self, user_id: int, points: int):
        self.points_data[str(user_id)] = max(0, points)
        self.save_data()

    def add_points(self, user_id: int, amount: int):
        current = self.get_user_points(user_id)
        self.set_user_points(user_id, current + amount)

    def get_user_roles_ids(self, member: discord.Member) -> list[int]:
        return [role.id for role in member.roles]

    def has_staff_role(self, member: discord.Member) -> bool:
        member_roles = self.get_user_roles_ids(member)

        staff_roles = set(self.promotion_chains.keys())
        staff_roles.add(CARGO_STAFF)
        staff_roles.add(CARGO_SECRETARIA)

        return any(role_id in staff_roles for role_id in member_roles)

    def is_secretaria(self, member: discord.Member) -> bool:
        return CARGO_SECRETARIA in self.get_user_roles_ids(member)

    def get_highest_staff_role(self, member: discord.Member):
        member_roles = self.get_user_roles_ids(member)

        for role_id in reversed(list(self.promotion_chains.keys())):
            if role_id in member_roles:
                return role_id

        return None

    async def check_and_promote(self, member: discord.Member) -> bool:
        current_role_id = self.get_highest_staff_role(member)

        if current_role_id is None:
            return False

        current_points = self.get_user_points(member.id)
        promotion_info = self.promotion_chains.get(current_role_id)

        if promotion_info.get("is_final"):
            return False

        points_needed = promotion_info["points_needed"]

        if current_points >= points_needed:
            next_role_id = promotion_info["next_role"]

            try:
                current_role = member.guild.get_role(current_role_id)
                next_role = member.guild.get_role(next_role_id)

                if current_role and next_role:
                    await member.remove_roles(current_role)
                    await member.add_roles(next_role)

                    self.set_user_points(member.id, 0)
                    return True

            except Exception as e:
                print(f"Erro ao promover {member}: {e}")
                return False

        return False

    @app_commands.command(
        name="ponto",
        description="adiciona ou remove pontos de um staff"
    )
    @app_commands.describe(
        staff="o staff que receberá os pontos",
        quantia="quantidade de pontos"
    )
    async def add_points_command(
        self,
        interaction: discord.Interaction,
        staff: discord.Member,
        quantia: int
    ):
        if not interaction.user.guild_permissions.administrator and not self.is_secretaria(interaction.user):
            await interaction.response.send_message(
                "❌ você não tem permissão para usar este comando",
                ephemeral=True
            )
            return

        if not self.has_staff_role(staff):
            await interaction.response.send_message(
                "❌ usuário não tem cargo da staff",
                ephemeral=True
            )
            return

        self.add_points(staff.id, quantia)
        new_points = self.get_user_points(staff.id)

        was_promoted = await self.check_and_promote(staff)

        if was_promoted:
            current_role_id = self.get_highest_staff_role(staff)
            role_name = self.promotion_chains[current_role_id]["role_name"]

            await interaction.response.send_message(
                f"🎉 promoção de staff!\n"
                f"{staff.mention} foi promovido para **{role_name}**!\n"
                f"pontos atuais: 0"
            )
            return

        current_role_id = self.get_highest_staff_role(staff)
        operation = f"+{quantia}" if quantia > 0 else str(quantia)

        if current_role_id:
            promotion_info = self.promotion_chains[current_role_id]

            if not promotion_info.get("is_final"):
                points_needed = promotion_info["points_needed"]
                next_role_id = promotion_info["next_role"]
                next_role_name = self.promotion_chains[next_role_id]["role_name"]

                message = (
                    f"📊 pontos atualizados\n"
                    f"pontos de {staff.mention} foram atualizados!\n"
                    f"operação: {operation}\n"
                    f"pontos totais: {new_points}\n"
                    f"próxima promoção: {next_role_name}: {new_points}/{points_needed} pontos"
                )
            else:
                message = (
                    f"📊 pontos atualizados\n"
                    f"pontos de {staff.mention} foram atualizados!\n"
                    f"operação: {operation}\n"
                    f"pontos totais: {new_points}\n"
                    f"status: ⭐ cargo máximo atingido!"
                )
        else:
            message = (
                f"📊 pontos atualizados\n"
                f"pontos de {staff.mention} foram atualizados!\n"
                f"operação: {operation}\n"
                f"pontos totais: {new_points}"
            )

        await interaction.response.send_message(message)

    @app_commands.command(
        name="remover_pontos",
        description="remove pontos de um staff"
    )
    @app_commands.describe(
        staff="o staff que perderá os pontos",
        quantia="quantidade de pontos a remover"
    )
    async def remove_points_command(
        self,
        interaction: discord.Interaction,
        staff: discord.Member,
        quantia: int
    ):
        if not interaction.user.guild_permissions.administrator and not self.is_secretaria(interaction.user):
            await interaction.response.send_message(
                "❌ você não tem permissão para usar este comando",
                ephemeral=True
            )
            return

        if not self.has_staff_role(staff):
            await interaction.response.send_message(
                "❌ usuário não tem cargo da staff",
                ephemeral=True
            )
            return

        current_points = self.get_user_points(staff.id)
        self.add_points(staff.id, -abs(quantia))
        new_points = self.get_user_points(staff.id)

        current_role_id = self.get_highest_staff_role(staff)

        if current_role_id:
            promotion_info = self.promotion_chains[current_role_id]

            if not promotion_info.get("is_final"):
                points_needed = promotion_info["points_needed"]
                next_role_id = promotion_info["next_role"]
                next_role_name = self.promotion_chains[next_role_id]["role_name"]

                message = (
                    f"🔴 pontos removidos\n"
                    f"pontos de {staff.mention} foram removidos!\n"
                    f"pontos removidos: -{abs(quantia)}\n"
                    f"pontos anteriores: {current_points}\n"
                    f"pontos atuais: {new_points}\n"
                    f"próxima promoção: {next_role_name}: {new_points}/{points_needed} pontos"
                )
            else:
                message = (
                    f"🔴 pontos removidos\n"
                    f"pontos de {staff.mention} foram removidos!\n"
                    f"pontos removidos: -{abs(quantia)}\n"
                    f"pontos anteriores: {current_points}\n"
                    f"pontos atuais: {new_points}"
                )
        else:
            message = (
                f"🔴 pontos removidos\n"
                f"pontos de {staff.mention} foram removidos!\n"
                f"pontos removidos: -{abs(quantia)}\n"
                f"pontos anteriores: {current_points}\n"
                f"pontos atuais: {new_points}"
            )

        await interaction.response.send_message(message)

    @app_commands.command(
        name="pontos",
        description="visualiza os pontos de um staff"
    )
    @app_commands.describe(staff="o staff para visualizar pontos")
    async def view_points_command(
        self,
        interaction: discord.Interaction,
        staff: discord.Member = None
    ):
        target = staff or interaction.user

        if not self.has_staff_role(target):
            await interaction.response.send_message(
                "❌ usuário não tem cargo da staff",
                ephemeral=True
            )
            return

        current_role_id = self.get_highest_staff_role(target)

        if current_role_id is None:
            await interaction.response.send_message(
                "❌ usuário não tem cargo da staff",
                ephemeral=True
            )
            return

        points = self.get_user_points(target.id)
        promotion_info = self.promotion_chains[current_role_id]
        role_name = promotion_info["role_name"]

        if not promotion_info.get("is_final"):
            next_role_id = promotion_info["next_role"]
            next_role_name = self.promotion_chains[next_role_id]["role_name"]
            points_needed = promotion_info["points_needed"]

            progress = min(points, points_needed)

            if points_needed > 0:
                bar_length = 10
                filled = int((progress / points_needed) * bar_length)
                bar = "█" * filled + "░" * (bar_length - filled)
            else:
                bar = "██████████"

            message = (
                f"📊 pontos de {target.name}\n"
                f"cargo atual: {role_name}\n"
                f"pontos totais: {points}\n"
                f"próxima promoção: {next_role_name}: {progress}/{points_needed} pontos\n"
                f"progresso: `{bar}`"
            )
        else:
            message = (
                f"📊 pontos de {target.name}\n"
                f"cargo atual: {role_name}\n"
                f"pontos totais: {points}\n"
                f"status: ⭐ cargo máximo atingido!"
            )

        await interaction.response.send_message(message)

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
        if not interaction.user.guild_permissions.administrator and not self.is_secretaria(interaction.user):
            await interaction.response.send_message(
                "❌ você não tem permissão para usar este comando",
                ephemeral=True
            )
            return

        if not self.has_staff_role(staff):
            await interaction.response.send_message(
                "❌ usuário não tem cargo da staff",
                ephemeral=True
            )
            return

        self.set_user_points(staff.id, 0)

        await interaction.response.send_message(
            f"🔄 pontos resetados\n"
            f"os pontos de {staff.mention} foram resetados para 0!"
        )

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ cog staff promotion carregado com sucesso!")


async def setup(bot):
    await bot.add_cog(StaffPromotion(bot))
