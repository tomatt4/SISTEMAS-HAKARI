import asyncio
import os
import random
import time
from enum import Enum

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# configurações
# ============================================================

ECONOMY_GUILD_ID = 1490679537019654294

DAILY_BONUS_ROLE_IDS = {
    1502738752106270831,
    1524830563003793429,
    1490782190064373983,
    1490679537019654303,
    1514699980538118164,
    1490679537032495297,
    1490679537032495295
}

MIN_TRANSACTION = 1
MAX_TRANSACTION = 500_000_000_000_000
DAILY_COOLDOWN_SECONDS = 24 * 60 * 60

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    raise RuntimeError(
        "A variável de ambiente DATABASE_URL não foi configurada."
    )

# Configurações de empregos
WORK_COOLDOWN_SECONDS = 15 * 60  # 15 minutos
FAILED_INTERVIEW_COOLDOWN_SECONDS = 24 * 60 * 60  # 24 horas
MONTHLY_CYCLE_SECONDS = 30 * 24 * 60 * 60  # 30 dias

# Dados dos empregos
class JobData(Enum):
    # (nome, salário mensal, chance de aprovação, meta mensal)
    ESTAGIARIO = ("Estagiário", 800, 0.90, 40)
    ENTREGADOR = ("Entregador", 1200, 0.80, 50)
    FAXINEIRO = ("Faxineiro", 1500, 0.80, 60)
    GARCOM = ("Garçom", 1800, 0.60, 70)
    ATENDENTE = ("Atendente", 2200, 0.50, 70)
    MOTORISTA = ("Motorista", 2800, 0.45, 70)
    MECANICO = ("Mecânico", 3500, 0.45, 70)
    PROGRAMADOR_JUNIOR = ("Programador Júnior", 4500, 0.45, 70)
    POLICIAL = ("Policial", 5000, 0.30, 80)
    BOMBEIRO = ("Bombeiro", 5500, 0.30, 80)
    ENFERMEIRO = ("Enfermeiro", 6000, 0.30, 80)
    PROFESSOR = ("Professor", 6500, 0.25, 95)
    DESENVOLVEDOR = ("Desenvolvedor", 8000, 0.15, 100)
    ADVOGADO = ("Advogado", 9000, 0.10, 150)
    MEDICO = ("Médico", 12000, 0.10, 150)
    EMPRESARIO = ("Empresário", 18000, 0.10, 150)
    CEO = ("CEO", 30000, 0.10, 150)

    def get_name(self):
        return self.value[0]

    def get_salary(self):
        return self.value[1]

    def get_approval_chance(self):
        return self.value[2]

    def get_monthly_goal(self):
        return self.value[3]


class JobStatus(Enum):
    ATIVO = "ativo"
    AFASTADO = "afastado"
    DEMITIDO = "demitido"


# ============================================================
# banco de dados
# ============================================================

class EconomyDatabase:
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
                    CREATE TABLE IF NOT EXISTS economy (
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        balance BIGINT NOT NULL DEFAULT 0 CHECK(balance >= 0),
                        last_daily BIGINT,
                        PRIMARY KEY (guild_id, user_id)
                    )
                    """
                )

                await connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jobs (
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        job_name TEXT NOT NULL,
                        salary BIGINT NOT NULL,
                        monthly_goal INTEGER NOT NULL,
                        work_count INTEGER NOT NULL DEFAULT 0,
                        hire_date BIGINT NOT NULL,
                        cycle_start_date BIGINT NOT NULL,
                        next_payment_date BIGINT NOT NULL,
                        last_work_date BIGINT,
                        robbery_count INTEGER NOT NULL DEFAULT 0,
                        suspension_end_date BIGINT,
                        status TEXT NOT NULL DEFAULT 'ativo',
                        PRIMARY KEY (guild_id, user_id)
                    )
                    """
                )

                await connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interview_cooldowns (
                        guild_id BIGINT NOT NULL,
                        user_id BIGINT NOT NULL,
                        retry_after BIGINT NOT NULL,
                        PRIMARY KEY (guild_id, user_id)
                    )
                    """
                )

                database_name = await connection.fetchval(
                    "SELECT current_database()"
                )
                total_accounts = await connection.fetchval(
                    "SELECT COUNT(*) FROM economy"
                )

                print(f"[ECONOMIA] PostgreSQL conectado: {database_name}")
                print(f"[ECONOMIA] Contas salvas: {total_accounts}")

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
    async def _ensure_account(
        connection: asyncpg.Connection,
        guild_id: int,
        user_id: int,
    ) -> None:
        await connection.execute(
            """
            INSERT INTO economy (guild_id, user_id, balance, last_daily)
            VALUES ($1, $2, 0, NULL)
            ON CONFLICT (guild_id, user_id) DO NOTHING
            """,
            guild_id,
            user_id,
        )

    async def get_balance(self, guild_id: int, user_id: int) -> int:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_account(connection, guild_id, user_id)

                balance = await connection.fetchval(
                    """
                    SELECT balance
                    FROM economy
                    WHERE guild_id = $1 AND user_id = $2
                    """,
                    guild_id,
                    user_id,
                )

                return int(balance)

    async def add_money(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
    ) -> int:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_account(connection, guild_id, user_id)

                balance = await connection.fetchval(
                    """
                    UPDATE economy
                    SET balance = balance + $1
                    WHERE guild_id = $2 AND user_id = $3
                    RETURNING balance
                    """,
                    amount,
                    guild_id,
                    user_id,
                )

                return int(balance)

    async def remove_money(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
    ) -> tuple[bool, int]:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_account(connection, guild_id, user_id)

                current_balance = await connection.fetchval(
                    """
                    SELECT balance
                    FROM economy
                    WHERE guild_id = $1 AND user_id = $2
                    FOR UPDATE
                    """,
                    guild_id,
                    user_id,
                )

                current_balance = int(current_balance)

                if current_balance < amount:
                    return False, current_balance

                new_balance = await connection.fetchval(
                    """
                    UPDATE economy
                    SET balance = balance - $1
                    WHERE guild_id = $2 AND user_id = $3
                    RETURNING balance
                    """,
                    amount,
                    guild_id,
                    user_id,
                )

                return True, int(new_balance)

    async def claim_daily(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
    ) -> tuple[bool, int, int]:
        now = int(time.time())
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_account(connection, guild_id, user_id)

                row = await connection.fetchrow(
                    """
                    SELECT balance, last_daily
                    FROM economy
                    WHERE guild_id = $1 AND user_id = $2
                    FOR UPDATE
                    """,
                    guild_id,
                    user_id,
                )

                last_daily = row["last_daily"]

                if last_daily is not None:
                    next_daily = int(last_daily) + DAILY_COOLDOWN_SECONDS

                    if now < next_daily:
                        remaining = next_daily - now
                        return False, remaining, next_daily

                next_daily = now + DAILY_COOLDOWN_SECONDS

                new_balance = await connection.fetchval(
                    """
                    UPDATE economy
                    SET balance = balance + $1, last_daily = $2
                    WHERE guild_id = $3 AND user_id = $4
                    RETURNING balance
                    """,
                    amount,
                    now,
                    guild_id,
                    user_id,
                )

                return True, int(new_balance), next_daily

    async def transfer_money(
        self,
        guild_id: int,
        sender_id: int,
        receiver_id: int,
        amount: int,
    ) -> tuple[bool, int, int]:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                await self._ensure_account(connection, guild_id, sender_id)
                await self._ensure_account(connection, guild_id, receiver_id)

                first_id, second_id = sorted((sender_id, receiver_id))

                await connection.fetch(
                    """
                    SELECT user_id
                    FROM economy
                    WHERE guild_id = $1
                      AND user_id IN ($2, $3)
                    ORDER BY user_id
                    FOR UPDATE
                    """,
                    guild_id,
                    first_id,
                    second_id,
                )

                sender_balance = int(
                    await connection.fetchval(
                        """
                        SELECT balance
                        FROM economy
                        WHERE guild_id = $1 AND user_id = $2
                        """,
                        guild_id,
                        sender_id,
                    )
                )

                receiver_balance = int(
                    await connection.fetchval(
                        """
                        SELECT balance
                        FROM economy
                        WHERE guild_id = $1 AND user_id = $2
                        """,
                        guild_id,
                        receiver_id,
                    )
                )

                if sender_balance < amount:
                    return False, sender_balance, receiver_balance

                new_sender_balance = await connection.fetchval(
                    """
                    UPDATE economy
                    SET balance = balance - $1
                    WHERE guild_id = $2 AND user_id = $3
                    RETURNING balance
                    """,
                    amount,
                    guild_id,
                    sender_id,
                )

                new_receiver_balance = await connection.fetchval(
                    """
                    UPDATE economy
                    SET balance = balance + $1
                    WHERE guild_id = $2 AND user_id = $3
                    RETURNING balance
                    """,
                    amount,
                    guild_id,
                    receiver_id,
                )

                return (
                    True,
                    int(new_sender_balance),
                    int(new_receiver_balance),
                )

    async def get_interview_cooldown(
        self,
        guild_id: int,
        user_id: int,
    ) -> int | None:
        now = int(time.time())
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            retry_after = await connection.fetchval(
                """
                SELECT retry_after
                FROM interview_cooldowns
                WHERE guild_id = $1 AND user_id = $2
                """,
                guild_id,
                user_id,
            )

            if retry_after is None:
                return None

            retry_after = int(retry_after)
            if retry_after <= now:
                await connection.execute(
                    """
                    DELETE FROM interview_cooldowns
                    WHERE guild_id = $1 AND user_id = $2
                    """,
                    guild_id,
                    user_id,
                )
                return None

            return retry_after

    async def set_interview_cooldown(
        self,
        guild_id: int,
        user_id: int,
    ) -> int:
        retry_after = int(time.time()) + FAILED_INTERVIEW_COOLDOWN_SECONDS
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            await connection.execute(
                """
                INSERT INTO interview_cooldowns (guild_id, user_id, retry_after)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE SET retry_after = EXCLUDED.retry_after
                """,
                guild_id,
                user_id,
                retry_after,
            )

        return retry_after

    async def clear_interview_cooldown(
        self,
        guild_id: int,
        user_id: int,
    ) -> None:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            await connection.execute(
                """
                DELETE FROM interview_cooldowns
                WHERE guild_id = $1 AND user_id = $2
                """,
                guild_id,
                user_id,
            )

    async def get_job(self, guild_id: int, user_id: int) -> dict | None:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT *
                FROM jobs
                WHERE guild_id = $1 AND user_id = $2
                """,
                guild_id,
                user_id,
            )

            return dict(row) if row else None

    async def hire_employee(
        self,
        guild_id: int,
        user_id: int,
        job_data: JobData,
    ) -> bool:
        now = int(time.time())
        next_payment = now + MONTHLY_CYCLE_SECONDS
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            result = await connection.execute(
                """
                INSERT INTO jobs (
                    guild_id,
                    user_id,
                    job_name,
                    salary,
                    monthly_goal,
                    hire_date,
                    cycle_start_date,
                    next_payment_date,
                    status
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (guild_id, user_id) DO NOTHING
                """,
                guild_id,
                user_id,
                job_data.get_name(),
                job_data.get_salary(),
                job_data.get_monthly_goal(),
                now,
                now,
                next_payment,
                JobStatus.ATIVO.value,
            )

            return result == "INSERT 0 1"

    async def work(self, guild_id: int, user_id: int) -> tuple[bool, str]:
        now = int(time.time())
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                job = await connection.fetchrow(
                    """
                    SELECT *
                    FROM jobs
                    WHERE guild_id = $1 AND user_id = $2
                    FOR UPDATE
                    """,
                    guild_id,
                    user_id,
                )

                if job is None:
                    return (
                        False,
                        "você não possui um emprego. use `/entrevista` "
                        "para participar de uma.",
                    )

                if job["status"] == JobStatus.DEMITIDO.value:
                    return (
                        False,
                        "você foi demitido. use `/demitir` antes de tentar "
                        "uma nova entrevista.",
                    )

                if job["status"] == JobStatus.AFASTADO.value:
                    suspension_end = job["suspension_end_date"]

                    if suspension_end and now < suspension_end:
                        return (
                            False,
                            f"você está afastado até <t:{suspension_end}:f>.",
                        )

                    await connection.execute(
                        """
                        UPDATE jobs
                        SET status = $1, suspension_end_date = NULL
                        WHERE guild_id = $2 AND user_id = $3
                        """,
                        JobStatus.ATIVO.value,
                        guild_id,
                        user_id,
                    )

                if job["last_work_date"] is not None:
                    next_work_time = (
                        int(job["last_work_date"]) + WORK_COOLDOWN_SECONDS
                    )

                    if now < next_work_time:
                        return (
                            False,
                            "você poderá trabalhar novamente em "
                            f"<t:{next_work_time}:R>.",
                        )

                if job["work_count"] >= job["monthly_goal"]:
                    return (
                        False,
                        "você já atingiu a meta mensal de "
                        f"{job['monthly_goal']} trabalhos.",
                    )

                new_work_count = int(job["work_count"]) + 1

                await connection.execute(
                    """
                    UPDATE jobs
                    SET work_count = $1, last_work_date = $2
                    WHERE guild_id = $3 AND user_id = $4
                    """,
                    new_work_count,
                    now,
                    guild_id,
                    user_id,
                )

                return (
                    True,
                    "você trabalhou com sucesso! progresso: "
                    f"{new_work_count}/{job['monthly_goal']}",
                )

    async def pay_salary(
        self,
        guild_id: int,
        user_id: int,
    ) -> tuple[bool, int]:
        now = int(time.time())
        next_payment = now + MONTHLY_CYCLE_SECONDS
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                job = await connection.fetchrow(
                    """
                    SELECT *
                    FROM jobs
                    WHERE guild_id = $1 AND user_id = $2
                    FOR UPDATE
                    """,
                    guild_id,
                    user_id,
                )

                if job is None:
                    return False, 0

                if job["work_count"] >= job["monthly_goal"]:
                    salary_earned = int(job["salary"])
                else:
                    salary_earned = int(
                        job["salary"]
                        * job["work_count"]
                        / job["monthly_goal"]
                    )

                await self._ensure_account(connection, guild_id, user_id)

                new_balance = await connection.fetchval(
                    """
                    UPDATE economy
                    SET balance = balance + $1
                    WHERE guild_id = $2 AND user_id = $3
                    RETURNING balance
                    """,
                    salary_earned,
                    guild_id,
                    user_id,
                )

                await connection.execute(
                    """
                    UPDATE jobs
                    SET
                        work_count = 0,
                        cycle_start_date = $1,
                        next_payment_date = $2
                    WHERE guild_id = $3 AND user_id = $4
                    """,
                    now,
                    next_payment,
                    guild_id,
                    user_id,
                )

                return True, int(new_balance)

    async def add_suspension(
        self,
        guild_id: int,
        user_id: int,
    ) -> tuple[bool, int]:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            async with connection.transaction():
                job = await connection.fetchrow(
                    """
                    SELECT *
                    FROM jobs
                    WHERE guild_id = $1 AND user_id = $2
                    FOR UPDATE
                    """,
                    guild_id,
                    user_id,
                )

                if job is None:
                    return False, 0

                now = int(time.time())
                robbery_count = int(job["robbery_count"]) + 1

                suspension_days = {
                    1: 5,
                    2: 10,
                    3: 15,
                    4: 20,
                    5: 25,
                    6: 30,
                    7: None,
                }

                if robbery_count >= 7:
                    await connection.execute(
                        """
                        UPDATE jobs
                        SET
                            status = $1,
                            robbery_count = $2,
                            suspension_end_date = NULL
                        WHERE guild_id = $3 AND user_id = $4
                        """,
                        JobStatus.DEMITIDO.value,
                        robbery_count,
                        guild_id,
                        user_id,
                    )

                    return True, 0

                days = suspension_days.get(robbery_count, 30)
                suspension_end = now + (days * 24 * 60 * 60)

                await connection.execute(
                    """
                    UPDATE jobs
                    SET
                        status = $1,
                        suspension_end_date = $2,
                        robbery_count = $3
                    WHERE guild_id = $4 AND user_id = $5
                    """,
                    JobStatus.AFASTADO.value,
                    suspension_end,
                    robbery_count,
                    guild_id,
                    user_id,
                )

                return True, suspension_end

    async def fire_employee(self, guild_id: int, user_id: int) -> bool:
        pool = await self._get_pool()

        async with pool.acquire() as connection:
            result = await connection.execute(
                """
                DELETE FROM jobs
                WHERE guild_id = $1 AND user_id = $2
                """,
                guild_id,
                user_id,
            )

            return result == "DELETE 1"


# ============================================================
# confirmação do pix
# ============================================================

class PixConfirmationView(discord.ui.View):
    def __init__(
        self,
        *,
        database: EconomyDatabase,
        guild_id: int,
        sender: discord.Member,
        receiver: discord.Member,
        amount: int,
    ):
        super().__init__(timeout=120)

        self.database = database
        self.guild_id = guild_id
        self.sender = sender
        self.receiver = receiver
        self.amount = amount

        self.finished = False
        self.message: discord.InteractionMessage | None = None

    async def interaction_check(
        self,
        interaction: discord.Interaction,
    ) -> bool:
        if interaction.user.id != self.receiver.id:
            await interaction.response.send_message(
                "apenas quem vai receber o pix pode confirmar ou recusar.",
                ephemeral=True,
            )
            return False

        return True

    def disable_all_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(
        label="confirmar pix",
        style=discord.ButtonStyle.green,
        emoji="<:check:1525566649384702023>",
    )
    async def confirm_pix(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.finished:
            await interaction.response.send_message(
                "<:check:1525566649384702023> | este pix já foi finalizado.",
                ephemeral=True,
            )
            return

        self.finished = True
        self.disable_all_buttons()

        success, sender_balance, receiver_balance = (
            await self.database.transfer_money(
                guild_id=self.guild_id,
                sender_id=self.sender.id,
                receiver_id=self.receiver.id,
                amount=self.amount,
            )
        )

        if not success:
            embed = discord.Embed(
                title="pix cancelado",
                description=(
                    f"<:negativobranco:1525565869407736029> | {self.sender.mention} não possui mais saldo suficiente "
                    "para concluir esta transferência."
                ),
                color=discord.Color.red(),
            )
            embed.add_field(
                name="<:carteira:1525566638685159484> | saldo atual",
                value=f"<:1183268890109808682:1525559694075236373> | R$ {sender_balance:,}".replace(",", "."),
                inline=False,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=self,
            )
            self.stop()
            return

        embed = discord.Embed(
            title="pix realizado com sucesso",
            description=(
                f"<:check:1525566649384702023> | {self.sender.mention} enviou "
                f"**R$ {self.amount:,}** para {self.receiver.mention}."
            ).replace(",", "."),
            color=discord.Color.green(),
        )
        embed.add_field(
            name=f"saldo de {self.sender.display_name}",
            value=f"<:1183268890109808682:1525559694075236373> | R$ {sender_balance:,}".replace(",", "."),
        )
        embed.add_field(
            name=f"saldo de {self.receiver.display_name}",
            value=f"<:1183268890109808682:1525559694075236373> | R$ {receiver_balance:,}".replace(",", "."),
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )
        self.stop()

    @discord.ui.button(
        label="recusar",
        style=discord.ButtonStyle.red,
        emoji="<:negativobranco:1525565869407736029>",
    )
    async def refuse_pix(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.finished:
            await interaction.response.send_message(
                "este pix já foi finalizado.",
                ephemeral=True,
            )
            return

        self.finished = True
        self.disable_all_buttons()

        embed = discord.Embed(
            title="pix recusado",
            description=(
                f"<:negativobranco:1525565869407736029> | {self.receiver.mention} recusou o pix de "
                f"**R$ {self.amount:,}** enviado por {self.sender.mention}."
            ).replace(",", "."),
            color=discord.Color.red(),
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )
        self.stop()

    async def on_timeout(self) -> None:
        if self.finished:
            return

        self.finished = True
        self.disable_all_buttons()

        if self.message is None:
            return

        embed = discord.Embed(
            title="pix expirado",
            description=(
                "<:negativobranco:1525565869407736029> | a confirmação não foi respondida dentro de 2 minutos. "
                "nenhum valor foi transferido."
            ),
            color=discord.Color.red(),
        )

        try:
            await self.message.edit(embed=embed, view=self)
        except discord.HTTPException:
            pass


# ============================================================
# seleção de profissões
# ============================================================

class JobSelectView(discord.ui.View):
    def __init__(self, database: EconomyDatabase, guild_id: int, user_id: int):
        super().__init__(timeout=60)
        self.database = database
        self.guild_id = guild_id
        self.user_id = user_id
        self.finished = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "apenas quem iniciou a entrevista pode escolher a profissão.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.select(
        placeholder="selecione uma profissão",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label=job.get_name(), value=job.name)
            for job in JobData
        ],
    )
    async def select_job(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ) -> None:
        if self.finished:
            await interaction.response.send_message(
                "esta entrevista já foi finalizada.",
                ephemeral=True,
            )
            return

        self.finished = True
        selected_job = JobData[select.values[0]]
        approval_chance = selected_job.get_approval_chance()
        approved = random.random() < approval_chance

        for item in self.children:
            item.disabled = True

        if approved:
            hired = await self.database.hire_employee(
                guild_id=self.guild_id,
                user_id=self.user_id,
                job_data=selected_job,
            )

            if not hired:
                await interaction.response.edit_message(
                    content="você já possui um emprego.",
                    embed=None,
                    view=self,
                )
                self.stop()
                return

            await self.database.clear_interview_cooldown(
                self.guild_id,
                self.user_id,
            )

            embed = discord.Embed(
                title="parabéns! você foi aprovado!",
                description=f"você é agora um(a) **{selected_job.get_name()}**.",
                color=discord.Color.green(),
            )
            embed.add_field(
                name="salário mensal",
                value=f"R$ {selected_job.get_salary():,}".replace(",", "."),
                inline=True,
            )
            embed.add_field(
                name="meta mensal",
                value=f"{selected_job.get_monthly_goal()} trabalhos",
                inline=True,
            )
            embed.add_field(
                name="próximo passo",
                value="use `/trabalhar` para começar!",
                inline=False,
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            retry_after = await self.database.set_interview_cooldown(
                self.guild_id,
                self.user_id,
            )
            embed = discord.Embed(
                title="reprovado na entrevista!",
                description=(
                    f"você não foi aprovado para **{selected_job.get_name()}**."
                ),
                color=discord.Color.red(),
            )
            embed.add_field(
                name="chance de aprovação",
                value=f"{approval_chance * 100:.0f}%",
                inline=True,
            )
            embed.add_field(
                name="próxima tentativa",
                value=f"<t:{retry_after}:R>",
                inline=True,
            )
            await interaction.response.edit_message(embed=embed, view=self)

        self.stop()


# ============================================================
# cog
# ============================================================

class Economia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.database = EconomyDatabase(DATABASE_URL)

    async def cog_load(self) -> None:
        await self.database.initialize()

    async def cog_unload(self) -> None:
        await self.database.close()

    @staticmethod
    def can_manage_economy(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False

        if interaction.user.id == interaction.guild.owner_id:
            return True

        if not isinstance(interaction.user, discord.Member):
            return False

        manager_role_id = 1491090814254841886
        return any(role.id == manager_role_id for role in interaction.user.roles)

    @app_commands.command(
        name="saldo",
        description="mostra o saldo atual do usuário ou de outra pessoa.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    @app_commands.describe(
        usuario="usuário para verificar o saldo (opcional, padrão é você).",
    )
    async def saldo(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member | None = None,
    ) -> None:
        target_user = usuario if usuario is not None else interaction.user

        if not isinstance(target_user, discord.Member):
            await interaction.response.send_message(
                "não foi possível obter informações do usuário.",
                ephemeral=True,
            )
            return

        balance = await self.database.get_balance(
            guild_id=interaction.guild_id,
            user_id=target_user.id,
        )

        if usuario is None:
            embed = discord.Embed(
                title="💰 carteira",
                description=f"## **R$ {balance:,}**".replace(",", "."),
                color=discord.Color.green()
            )

            embed.add_field(
                name="👤 usuário",
                value=interaction.user.mention,
                inline=True
            )

            embed.add_field(
                name="📅 consultado",
                value=f"<t:{int(discord.utils.utcnow().timestamp())}:f>",
                inline=False
            )

        else:
            embed = discord.Embed(
                title=f"💰 carteira de {target_user.display_name}",
                description=f"## **R$ {balance:,}**".replace(",", "."),
                color=discord.Color.blurple()
            )

            embed.add_field(
                name="👤 usuário",
                value=target_user.mention,
                inline=True
            )

            embed.add_field(
                name="📅 consultado",
                value=f"<t:{int(discord.utils.utcnow().timestamp())}:f>",
                inline=False
            )

        embed.set_thumbnail(url=target_user.display_avatar.url)

        embed.set_footer(
            text=f"solicitado por {interaction.user.display_name} | sistema de economia por mattzaddas",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="addreais",
        description="adiciona reais ao saldo de um usuário.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    @app_commands.describe(
        usuario="usuário que receberá os reais.",
        quantia="quantidade entre 1 e 500 trilhões reais.",
    )
    async def addreais(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        quantia: app_commands.Range[int, MIN_TRANSACTION, MAX_TRANSACTION],
    ) -> None:
        if not self.can_manage_economy(interaction):
            await interaction.response.send_message(
                "apenas o dono do servidor ou o cargo autorizado pode usar este comando.",
                ephemeral=True,
            )
            return

        new_balance = await self.database.add_money(
            guild_id=interaction.guild_id,
            user_id=usuario.id,
            amount=quantia,
        )

        await interaction.response.send_message(
            (
                f"adicionei **R$ {quantia:,}** para {usuario.mention}.\n"
                f"novo saldo: **R$ {new_balance:,}**."
            ).replace(",", "."),
        )


    @app_commands.command(
        name="daily",
        description="resgata uma recompensa diária em reais.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    async def daily(
        self,
        interaction: discord.Interaction,
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        base_amount = random.randint(100, 300)

        has_bonus_role = any(
            role.id in DAILY_BONUS_ROLE_IDS
            for role in interaction.user.roles
        )

        amount = int(base_amount * 1.5) if has_bonus_role else base_amount

        claimed, value, next_daily = await self.database.claim_daily(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
            amount=amount,
        )

        if not claimed:
            await interaction.response.send_message(
                (
                    "você já resgatou seu daily.\n"
                    f"tente novamente <t:{next_daily}:R>."
                ),
            )
            return

        bonus_text = (
            "\nbônus de cargo **1,5x** aplicado."
            if has_bonus_role
            else ""
        )

        await interaction.response.send_message(
            (
                f"<:check:1525566649384702023> | você recebeu **R$ {amount:,}** no daily."
                f"{bonus_text}\n"
                f"<:1183268890109808682:1525559694075236373> | seu saldo agora é **R$ {value:,}**.\n"
                f"<:calendar:1525579207818608682> | próximo daily: <t:{next_daily}:R>."
            ).replace(",", "."),
        )

    @app_commands.command(
        name="pix",
        description="envia reais para outro usuário após a confirmação dele.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    @app_commands.describe(
        usuario="usuário que receberá o pix.",
        quantia="quantidade entre 1 e 500.000.000.000.000 reais.",
    )
    async def pix(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        quantia: app_commands.Range[int, MIN_TRANSACTION, MAX_TRANSACTION],
    ) -> None:
        if not isinstance(interaction.user, discord.Member):
            return

        if usuario.id == interaction.user.id:
            await interaction.response.send_message(
                "<:negativobranco:1525565869407736029> | você não pode enviar um pix para si mesmo.",
                ephemeral=True,
            )
            return

        if usuario.bot:
            await interaction.response.send_message(
                "<:negativobranco:1525565869407736029> | você não pode enviar um pix para bots.",
                ephemeral=True,
            )
            return

        sender_balance = await self.database.get_balance(
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
        )

        if sender_balance < quantia:
            await interaction.response.send_message(
                (
                    f"<:negativobranco:1525565869407736029> | saldo insuficiente. você possui **R$ {sender_balance:,}**."
                ).replace(",", "."),
                ephemeral=True,
            )
            return

        view = PixConfirmationView(
            database=self.database,
            guild_id=interaction.guild_id,
            sender=interaction.user,
            receiver=usuario,
            amount=quantia,
        )

        embed = discord.Embed(
            title="confirmação de pix",
            description=(
                f"<a:white_exclamation:1522707377835737139>| {interaction.user.mention} quer enviar "
                f"**R$ {quantia:,}** para você.\n\n"
                "confirme ou recuse usando os botões abaixo."
            ).replace(",", "."),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="a solicitação expira em 2 minutos.")

        await interaction.response.send_message(
            content=usuario.mention,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(users=True),
        )

        view.message = await interaction.original_response()

    @app_commands.command(
        name="remover_reais",
        description="remove reais do saldo de um usuário.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    @app_commands.describe(
        usuario="usuário que terá reais removidos.",
        quantia="quantidade de reais que será removida.",
    )
    async def remover_reais(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        quantia: app_commands.Range[int, 1, MAX_TRANSACTION],
    ) -> None:
        if not self.can_manage_economy(interaction):
            await interaction.response.send_message(
                "apenas o dono do servidor ou o cargo autorizado pode usar este comando.",
                ephemeral=True,
            )
            return

        success, new_balance = await self.database.remove_money(
            guild_id=interaction.guild_id,
            user_id=usuario.id,
            amount=quantia,
        )

        if not success:
            await interaction.response.send_message(
                (
                    f"<:negativobranco:1525565869407736029> | {usuario.mention} não possui **R$ {quantia:,}**.\n"
                    f"<:1183268890109808682:1525559694075236373> | saldo atual: **R$ {new_balance:,}**."
                ).replace(",", "."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            (
                f"removi **R$ {quantia:,}** de {usuario.mention}.\n"
                f"<:1183268890109808682:1525559694075236373> | novo saldo: **R$ {new_balance:,}**."
            ).replace(",", "."),
            ephemeral=False,
        )

    # ======================== JOBS COMMANDS ========================

    @app_commands.command(
        name="entrevista",
        description="participe de uma entrevista de emprego.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    async def entrevista(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Abre o seletor de profissões para a entrevista"""
        job = await self.database.get_job(interaction.guild_id, interaction.user.id)

        if job is not None:
            await interaction.response.send_message(
                "<:negativobranco:1525565869407736029> | você já possui um emprego! use `/demitir` para sair do atual.",
                ephemeral=True,
            )
            return

        retry_after = await self.database.get_interview_cooldown(
            interaction.guild_id,
            interaction.user.id,
        )
        if retry_after is not None:
            await interaction.response.send_message(
                f"você poderá fazer outra entrevista <t:{retry_after}:R>.",
                ephemeral=True,
            )
            return

        view = JobSelectView(
            database=self.database,
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
        )

        embed = discord.Embed(
            title="entrevista de emprego",
            description="escolha uma profissão para participar da entrevista.",
            color=discord.Color.blurple(),
        )

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(
        name="trabalhar",
        description="trabalhe para ganhar dinheiro.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    async def trabalhar(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Registra um trabalho para o usuário"""
        success, message = await self.database.work(interaction.guild_id, interaction.user.id)

        if success:
            await interaction.response.send_message(message)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(
        name="emprego",
        description="mostra informações sobre seu emprego atual.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    async def emprego(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Mostra informações do emprego"""
        job = await self.database.get_job(interaction.guild_id, interaction.user.id)

        if job is None:
            await interaction.response.send_message(
                "<:negativobranco:1525565869407736029> | você não possui um emprego. use `/entrevista` para participar de uma.",
                ephemeral=True,
            )
            return

        status_emoji = {
            JobStatus.ATIVO.value: "✅",
            JobStatus.AFASTADO.value: "⏸️",
            JobStatus.DEMITIDO.value: "❌",
        }

        embed = discord.Embed(
            title=f"<:indentify:1525579201262911629> | informações de emprego",
            description=f"{status_emoji.get(job['status'], '❓')} {job['job_name']}",
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="<:1183268890109808682:1525559694075236373> | salário mensal",
            value=f"R$ {job['salary']:,}".replace(",", "."),
            inline=True,
        )

        embed.add_field(
            name="<:student:1525566394245316638> | meta mensal",
            value=f"{job['work_count']}/{job['monthly_goal']} trabalhos",
            inline=True,
        )

        embed.add_field(
            name="<:condecoracoes:1525566668238094428> | contratado em",
            value=f"<t:{job['hire_date']}:d>",
            inline=True,
        )

        embed.add_field(
            name="<:1183268890109808682:1525559694075236373> | próximo pagamento",
            value=f"<t:{job['next_payment_date']}:R>",
            inline=True,
        )

        if job["status"] == JobStatus.AFASTADO.value and job["suspension_end_date"]:
            embed.add_field(
                name="<:indentify:1525579201262911629> | volta ao trabalho",
                value=f"<t:{job['suspension_end_date']}:f>",
                inline=True,
            )

        embed.add_field(
            name="<:clock:1525566652123447307> | infrações",
            value=f"{job['robbery_count']}/7",
            inline=True,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="salario",
        description="receba seu salário quando o ciclo mensal terminar.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    async def salario(self, interaction: discord.Interaction) -> None:
        job = await self.database.get_job(
            interaction.guild_id,
            interaction.user.id,
        )

        if job is None:
            await interaction.response.send_message(
                "você não possui um emprego.",
                ephemeral=True,
            )
            return

        now = int(time.time())
        if now < int(job["next_payment_date"]):
            await interaction.response.send_message(
                f"seu próximo pagamento estará disponível <t:{job['next_payment_date']}:R>.",
                ephemeral=True,
            )
            return

        previous_balance = await self.database.get_balance(
            interaction.guild_id,
            interaction.user.id,
        )
        paid, new_balance = await self.database.pay_salary(
            interaction.guild_id,
            interaction.user.id,
        )

        if not paid:
            await interaction.response.send_message(
                "não foi possível processar seu salário.",
                ephemeral=True,
            )
            return

        earned = new_balance - previous_balance
        await interaction.response.send_message(
            (
                f"<:check:1525566649384702023> | salário recebido: **R$ {earned:,}**.\n"
                f"<:1183268890109808682:1525559694075236373> | novo saldo: **R$ {new_balance:,}**."
            ).replace(",", ".")
        )

    @app_commands.command(
        name="demitir",
        description="saia do seu emprego atual.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    async def demitir(
        self,
        interaction: discord.Interaction,
    ) -> None:
        """Demite o usuário do emprego"""
        success = await self.database.fire_employee(interaction.guild_id, interaction.user.id)

        if not success:
            await interaction.response.send_message(
                "você não possui um emprego.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("<:student:1525566394245316638> | você saiu do seu emprego.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economia(bot))
