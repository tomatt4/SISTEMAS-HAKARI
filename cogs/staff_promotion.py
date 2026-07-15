import asyncio
import os
import time
from enum import Enum

import asyncpg
import discord
from discord.ext import commands
from discord import app_commands


# ============================================================
# configurações
# ============================================================

CARGO_STAFF = 1500969290093039626
CARGO_SECRETARIA = 1513653295061798922

DATABASE_STAFF_PROMOTION = os.getenv("DATABASE_STAFF_PROMOTION", "").strip()

if not DATABASE_STAFF_PROMOTION:
    raise RuntimeError(
        "Cadê a variável DATABASE_STAFF_PROMOTION???"
    )


# ============================================================
# banco de dados
# ============================================================

class StaffPromotionDatabase:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: asyncpg.Pool | None = None
        self.init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        if self.pool is not None:
            return

        async with self.init_lock:
            if self.pool is not None:
                return

            self.pool = await asyncpg.create_pool(
                dsn=self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )

            async with self.pool.acquire() as connection:
                await connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS staff_promotion (
                        user_id BIGINT PRIMARY KEY,
                        points BIGINT NOT NULL DEFAULT 0 CHECK(points >= 0),
                        last_updated BIGINT
                    )
                    """
                )

                total_records = await connection.fetchval(
                    "SELECT COUNT(*) FROM staff_promotion"
                )

                database_name = await connection.fetchval(
                    "SELECT current_database()"
                )

                print(f"[STAFF PROMOTION] PostgreSQL conectado: {database_name}")
                print(f"[STAFF PROMOTION] Registros salvos: {total_records}")

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def _get_pool(self) -> asyncpg.Pool:
        await self.initialize()

        if self.pool is None:
            raise RuntimeError("O pool do PostgreSQL não foi inicializado.")

        return self.pool

    @staticmethod
    async def _ensure_user(
        connection: asyncpg.Connection,
        user_id: int,
    ) -> None:
        await connection.execute(
            """
            INSERT INTO staff_promotion (user_id, points, last_updated)
            VALUES ($1, 0, NULL)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id,
        )

    async def get_points(self, user_id: int) -> int:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_user(connection, user_id)

                points = await connection.fetchval(
                    """
                    SELECT points
                    FROM staff_promotion
                    WHERE user_id = $1
                    """,
                    user_id,
                )

                return int(points) if points is not None else 0

    async def set_points(self, user_id: int, points: int) -> None:
        pool = await self._get_pool()
        now = int(time.time())

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_user(connection, user_id)

                await connection.execute(
                    """
                    UPDATE staff_promotion
                    SET points = $1, last_updated = $2
                    WHERE user_id = $3
                    """,
                    max(0, points),
                    now,
                    user_id,
                )

    async def add_points(self, user_id: int, amount: int) -> int:
        pool = await self._get_pool()
        now = int(time.time())

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_user(connection, user_id)

                new_points = await connection.fetchval(
                    """
                    UPDATE staff_promotion
                    SET points = points + $1, last_updated = $2
                    WHERE user_id = $3
                    RETURNING points
                    """,
                    amount,
                    now,
                    user_id,
                )

                return int(new_points) if new_points is not None else 0


# ============================================================
# cog
# ============================================================

class StaffPromotion(commands.Cog):
    """Sistema de promoção de staffs baseado em pontuação"""

    def __init__(self, bot):
        self.bot = bot
        self.database = StaffPromotionDatabase(DATABASE_STAFF_PROMOTION)

        self.promotion_chains = {
            # 1. Staff (ID 1490679537032495301) -> Próximo: Moderador (ID 1519102905112858757)
            1490679537032495301: {
                "next_role": 1519102905112858757,
                "points_needed": 10,
                "role_name": "staff"
            },
            # 2. Moderador (ID 1519102905112858757) -> Próximo: Supervisor (ID 1490679537032495298)
            1519102905112858757: {
                "next_role": 1490679537032495298,
                "points_needed": 20,
                "role_name": "moderador"
            },
            # 3. Supervisor (ID 1490679537032495298) -> Próximo: Coordenador (ID 1519102475246899341)
            1490679537032495298: {
                "next_role": 1519102475246899341,
                "points_needed": 30,
                "role_name": "supervisor"
            },
            # 4. Coordenador (ID 1519102475246899341) -> Próximo: Diretor (ID 1490679537032495302)
            1519102475246899341: {
                "next_role": 1490679537032495302,
                "points_needed": 40,
                "role_name": "coordenador"
            },
            # 5. Diretor (ID 1490679537032495302) -> Próximo: Administrador (ID 1518394774414037042)
            1490679537032495302: {
                "next_role": 1518394774414037042,
                "points_needed": 50,
                "role_name": "diretor"
            },
            # 6. Administrador (ID 1518394774414037042) -> Próximo: Gerente (ID 1490679537032495303)
            1518394774414037042: {
                "next_role": 1490679537032495303,
                "additional_roles": [1513653295061798922],
                "points_needed": 70,
                "role_name": "administrador"
            },
            # 7. Gerente (ID 1490679537032495303) -> Próximo: Sub Owner (ID 1496282936331337789)
            1490679537032495303: {
                "next_role": 1496282936331337789,
                "points_needed": 140,
                "role_name": "gerente"
            },
            # 8. Sub Owner (ID 1496282936331337789) -> Cargo Máximo Final por pontos
            1496282936331337789: {
                "next_role": None,
                "points_needed": 0,
                "role_name": "sub owner",
                "is_final": True
            }
        }

    async def cog_load(self) -> None:
        await self.database.initialize()

    async def cog_unload(self) -> None:
        await self.database.close()

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

        current_points = await self.database.get_points(member.id)
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

                    # Adicionar roles adicionais se existirem
                    additional_roles = promotion_info.get("additional_roles", [])
                    for role_id in additional_roles:
                        role = member.guild.get_role(role_id)
                        if role:
                            await member.add_roles(role)

                    await self.database.set_points(member.id, 0)
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

        await self.database.add_points(staff.id, quantia)
        new_points = await self.database.get_points(staff.id)

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

        current_points = await self.database.get_points(staff.id)
        await self.database.add_points(staff.id, -abs(quantia))
        new_points = await self.database.get_points(staff.id)

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

        points = await self.database.get_points(target.id)
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

        await self.database.set_points(staff.id, 0)

        await interaction.response.send_message(
            f"🔄 pontos resetados\n"
            f"os pontos de {staff.mention} foram resetados para 0!"
        )

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ cog staff promotion carregado com sucesso!")


async def setup(bot):
    await bot.add_cog(StaffPromotion(bot))
