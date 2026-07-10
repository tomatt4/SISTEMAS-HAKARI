import asyncio
import random
import sqlite3
import time
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURAÇÕES
# ============================================================

ECONOMY_GUILD_ID = 1500231901397516340

DAILY_BONUS_ROLE_IDS = {
    1502738752106270831,
    1524830563003793429,
}

MIN_TRANSACTION = 3
MAX_TRANSACTION = 1_250_000
DAILY_COOLDOWN_SECONDS = 24 * 60 * 60

DATABASE_PATH = Path("data") / "economia.db"


# ============================================================
# BANCO DE DADOS
# ============================================================

class EconomyDatabase:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self.lock = asyncio.Lock()

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def _create_tables(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA foreign_keys=ON;")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS economy (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0),
                    last_daily INTEGER,
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )

    @staticmethod
    def _ensure_account(
        connection: sqlite3.Connection,
        guild_id: int,
        user_id: int,
    ) -> None:
        connection.execute(
            """
            INSERT OR IGNORE INTO economy (guild_id, user_id, balance, last_daily)
            VALUES (?, ?, 0, NULL)
            """,
            (guild_id, user_id),
        )

    async def get_balance(self, guild_id: int, user_id: int) -> int:
        async with self.lock:
            with self._connect() as connection:
                self._ensure_account(connection, guild_id, user_id)

                row = connection.execute(
                    """
                    SELECT balance
                    FROM economy
                    WHERE guild_id = ? AND user_id = ?
                    """,
                    (guild_id, user_id),
                ).fetchone()

                return int(row["balance"])

    async def add_money(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
    ) -> int:
        async with self.lock:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")

                try:
                    self._ensure_account(connection, guild_id, user_id)

                    connection.execute(
                        """
                        UPDATE economy
                        SET balance = balance + ?
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (amount, guild_id, user_id),
                    )

                    row = connection.execute(
                        """
                        SELECT balance
                        FROM economy
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (guild_id, user_id),
                    ).fetchone()

                    connection.execute("COMMIT")
                    return int(row["balance"])

                except Exception:
                    connection.execute("ROLLBACK")
                    raise

    async def remove_money(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
    ) -> tuple[bool, int]:
        async with self.lock:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")

                try:
                    self._ensure_account(connection, guild_id, user_id)

                    row = connection.execute(
                        """
                        SELECT balance
                        FROM economy
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (guild_id, user_id),
                    ).fetchone()

                    current_balance = int(row["balance"])

                    if current_balance < amount:
                        connection.execute("ROLLBACK")
                        return False, current_balance

                    new_balance = current_balance - amount

                    connection.execute(
                        """
                        UPDATE economy
                        SET balance = ?
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (new_balance, guild_id, user_id),
                    )

                    connection.execute("COMMIT")
                    return True, new_balance

                except Exception:
                    connection.execute("ROLLBACK")
                    raise

    async def claim_daily(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
    ) -> tuple[bool, int, int]:
        """
        Retorna:
        - resgatado: bool
        - saldo ou segundos restantes: int
        - próximo timestamp: int
        """
        now = int(time.time())

        async with self.lock:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")

                try:
                    self._ensure_account(connection, guild_id, user_id)

                    row = connection.execute(
                        """
                        SELECT balance, last_daily
                        FROM economy
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (guild_id, user_id),
                    ).fetchone()

                    last_daily = row["last_daily"]

                    if last_daily is not None:
                        next_daily = int(last_daily) + DAILY_COOLDOWN_SECONDS

                        if now < next_daily:
                            remaining = next_daily - now
                            connection.execute("ROLLBACK")
                            return False, remaining, next_daily

                    new_balance = int(row["balance"]) + amount
                    next_daily = now + DAILY_COOLDOWN_SECONDS

                    connection.execute(
                        """
                        UPDATE economy
                        SET balance = ?, last_daily = ?
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (new_balance, now, guild_id, user_id),
                    )

                    connection.execute("COMMIT")
                    return True, new_balance, next_daily

                except Exception:
                    connection.execute("ROLLBACK")
                    raise

    async def transfer_money(
        self,
        guild_id: int,
        sender_id: int,
        receiver_id: int,
        amount: int,
    ) -> tuple[bool, int, int]:
        """
        Retorna:
        - transferido: bool
        - saldo do remetente
        - saldo do destinatário
        """
        async with self.lock:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")

                try:
                    self._ensure_account(connection, guild_id, sender_id)
                    self._ensure_account(connection, guild_id, receiver_id)

                    sender_row = connection.execute(
                        """
                        SELECT balance
                        FROM economy
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (guild_id, sender_id),
                    ).fetchone()

                    receiver_row = connection.execute(
                        """
                        SELECT balance
                        FROM economy
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (guild_id, receiver_id),
                    ).fetchone()

                    sender_balance = int(sender_row["balance"])
                    receiver_balance = int(receiver_row["balance"])

                    if sender_balance < amount:
                        connection.execute("ROLLBACK")
                        return False, sender_balance, receiver_balance

                    new_sender_balance = sender_balance - amount
                    new_receiver_balance = receiver_balance + amount

                    connection.execute(
                        """
                        UPDATE economy
                        SET balance = ?
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (new_sender_balance, guild_id, sender_id),
                    )

                    connection.execute(
                        """
                        UPDATE economy
                        SET balance = ?
                        WHERE guild_id = ? AND user_id = ?
                        """,
                        (new_receiver_balance, guild_id, receiver_id),
                    )

                    connection.execute("COMMIT")
                    return True, new_sender_balance, new_receiver_balance

                except Exception:
                    connection.execute("ROLLBACK")
                    raise


# ============================================================
# CONFIRMAÇÃO DO PIX
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
                "Apenas quem vai receber o PIX pode confirmar ou recusar.",
                ephemeral=True,
            )
            return False

        return True

    def disable_all_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(
        label="Confirmar PIX",
        style=discord.ButtonStyle.green,
        emoji="✅",
    )
    async def confirm_pix(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.finished:
            await interaction.response.send_message(
                "Este PIX já foi finalizado.",
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
                title="PIX cancelado",
                description=(
                    f"{self.sender.mention} não possui mais saldo suficiente "
                    "para concluir esta transferência."
                ),
                color=discord.Color.red(),
            )
            embed.add_field(
                name="Saldo atual",
                value=f"R$ {sender_balance:,}".replace(",", "."),
                inline=False,
            )

            await interaction.response.edit_message(
                embed=embed,
                view=self,
            )
            self.stop()
            return

        embed = discord.Embed(
            title="PIX realizado com sucesso",
            description=(
                f"{self.sender.mention} enviou "
                f"**R$ {self.amount:,}** para {self.receiver.mention}."
            ).replace(",", "."),
            color=discord.Color.green(),
        )
        embed.add_field(
            name=f"Saldo de {self.sender.display_name}",
            value=f"R$ {sender_balance:,}".replace(",", "."),
        )
        embed.add_field(
            name=f"Saldo de {self.receiver.display_name}",
            value=f"R$ {receiver_balance:,}".replace(",", "."),
        )

        await interaction.response.edit_message(
            embed=embed,
            view=self,
        )
        self.stop()

    @discord.ui.button(
        label="Recusar",
        style=discord.ButtonStyle.red,
        emoji="✖️",
    )
    async def refuse_pix(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if self.finished:
            await interaction.response.send_message(
                "Este PIX já foi finalizado.",
                ephemeral=True,
            )
            return

        self.finished = True
        self.disable_all_buttons()

        embed = discord.Embed(
            title="PIX recusado",
            description=(
                f"{self.receiver.mention} recusou o PIX de "
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
            title="PIX expirado",
            description=(
                "A confirmação não foi respondida dentro de 2 minutos. "
                "Nenhum valor foi transferido."
            ),
            color=discord.Color.orange(),
        )

        try:
            await self.message.edit(embed=embed, view=self)
        except discord.HTTPException:
            pass


# ============================================================
# COG
# ============================================================

class Economia(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.database = EconomyDatabase(DATABASE_PATH)

    @staticmethod
    def is_guild_owner(interaction: discord.Interaction) -> bool:
        return (
            interaction.guild is not None
            and interaction.guild.owner_id == interaction.user.id
        )

    @app_commands.command(
        name="addreais",
        description="Adiciona reais ao saldo de um usuário.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    @app_commands.describe(
        usuario="Usuário que receberá os reais.",
        quantia="Quantidade entre 3 e 1.250.000 reais.",
    )
    async def addreais(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        quantia: app_commands.Range[int, MIN_TRANSACTION, MAX_TRANSACTION],
    ) -> None:
        if not self.is_guild_owner(interaction):
            await interaction.response.send_message(
                "Apenas o dono com posse do servidor pode usar este comando.",
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
                f"Adicionei **R$ {quantia:,}** para {usuario.mention}.\n"
                f"Novo saldo: **R$ {new_balance:,}**."
            ).replace(",", "."),
            ephemeral=True,
        )

    @app_commands.command(
        name="daily",
        description="Resgata uma recompensa diária em reais.",
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
                    "Você já resgatou seu daily.\n"
                    f"Tente novamente <t:{next_daily}:R>."
                ),
                ephemeral=True,
            )
            return

        bonus_text = (
            "\nBônus de cargo **1,5x** aplicado."
            if has_bonus_role
            else ""
        )

        await interaction.response.send_message(
            (
                f"Você recebeu **R$ {amount:,}** no daily."
                f"{bonus_text}\n"
                f"Seu saldo agora é **R$ {value:,}**.\n"
                f"Próximo daily: <t:{next_daily}:R>."
            ).replace(",", "."),
            ephemeral=True,
        )

    @app_commands.command(
        name="pix",
        description="Envia reais para outro usuário após a confirmação dele.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    @app_commands.describe(
        usuario="Usuário que receberá o PIX.",
        quantia="Quantidade entre 3 e 1.250.000 reais.",
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
                "Você não pode enviar um PIX para si mesmo.",
                ephemeral=True,
            )
            return

        if usuario.bot:
            await interaction.response.send_message(
                "Você não pode enviar um PIX para bots.",
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
                    f"Saldo insuficiente. Você possui **R$ {sender_balance:,}**."
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
            title="Confirmação de PIX",
            description=(
                f"{usuario.mention}, {interaction.user.mention} quer enviar "
                f"**R$ {quantia:,}** para você.\n\n"
                "Confirme ou recuse usando os botões abaixo."
            ).replace(",", "."),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="A solicitação expira em 2 minutos.")

        await interaction.response.send_message(
            content=usuario.mention,
            embed=embed,
            view=view,
            allowed_mentions=discord.AllowedMentions(users=True),
        )

        view.message = await interaction.original_response()

    @app_commands.command(
        name="remover_reais",
        description="Remove reais do saldo de um usuário.",
    )
    @app_commands.guilds(discord.Object(id=ECONOMY_GUILD_ID))
    @app_commands.describe(
        usuario="Usuário que terá reais removidos.",
        quantia="Quantidade de reais que será removida.",
    )
    async def remover_reais(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        quantia: app_commands.Range[int, 1, MAX_TRANSACTION],
    ) -> None:
        if not self.is_guild_owner(interaction):
            await interaction.response.send_message(
                "apenas o dono com posse do servidor pode usar este comando.",
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
                    f"{usuario.mention} não possui **R$ {quantia:,}**.\n"
                    f"saldo atual: **R$ {new_balance:,}**."
                ).replace(",", "."),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            (
                f"removi **R$ {quantia:,}** de {usuario.mention}.\n"
                f"novo saldo: **R$ {new_balance:,}**."
            ).replace(",", "."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economia(bot))

    # sincroniza so em um servidor
    # ai o resto do servidor nem aparece esses comandos
    guild = discord.Object(id=ECONOMY_GUILD_ID)
    await bot.tree.sync(guild=guild)
