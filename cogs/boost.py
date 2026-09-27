import asyncio
from io import BytesIO
import json
import os
import re
from pathlib import Path

import aiohttp
import asyncpg
import discord
from PIL import Image, UnidentifiedImageError
from discord.ext import commands


BOOSTER_ROLE_ID = 1553817043076259911
ROLE_POSITION_UPPER_ID = 1553842552237457510
ROLE_POSITION_LOWER_ID = 1553840828684963860
REPAIR_BELOW_ROLE_ID = 1553832823264116796
MANAGED_ROLE_PREFIXES = ("família -", "familia -", "cargo -")
FAMILY_MEMBER_LIMIT = 15


class RoleEditModal(discord.ui.Modal):
    def __init__(self, cog, owner_id: int, role_id: int, family: bool):
        self.cog = cog
        self.owner_id = owner_id
        self.role_id = role_id
        self.family = family
        role_name = "Editar cargo da família" if family else "Editar seu cargo"
        super().__init__(
            title=role_name,
            custom_id=f"boost:edit:{owner_id}:{role_id}",
        )

        guild = cog.bot.get_guild(cog.guild_id_for_role(role_id))
        current_role = guild.get_role(role_id) if guild else None
        current_name = current_role.name if current_role else ""
        current_color = (
            f"#{current_role.color.value:06X}" if current_role else "#000000"
        )

        self.name_input = discord.ui.TextInput(
            label="Nome do cargo",
            placeholder="Digite o nome do cargo",
            default=current_name,
            max_length=100,
            required=True,
        )
        self.color_input = discord.ui.TextInput(
            label="Cor hexadecimal",
            placeholder="#000000 ou 000000",
            default=current_color,
            min_length=6,
            max_length=7,
            required=True,
        )
        self.add_item(self.name_input)
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "Esse formulário pertence a outra pessoa.", ephemeral=True
            )
        if not self.cog.is_booster(interaction.user):
            return await interaction.response.send_message(
                "Este comando é exclusivo para boosters.", ephemeral=True
            )

        color_text = self.color_input.value.strip()
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", color_text):
            return await interaction.response.send_message(
                "Informe uma cor hexadecimal válida, como `000000` ou `#000000`.",
                ephemeral=True,
            )
        role_name = self.name_input.value.strip()
        if not role_name:
            return await interaction.response.send_message(
                "O nome do cargo não pode ficar vazio.", ephemeral=True
            )

        role = interaction.guild.get_role(self.role_id)
        if role is None:
            return await interaction.response.send_message(
                "Não encontrei esse cargo no servidor.", ephemeral=True
            )

        try:
            role = await role.edit(
                name=role_name,
                color=discord.Color(int(color_text.removeprefix("#"), 16)),
                reason=f"Personalização solicitada por {interaction.user}",
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "Não tenho permissão para editar esse cargo.", ephemeral=True
            )
        except discord.HTTPException:
            return await interaction.response.send_message(
                "O Discord não conseguiu atualizar o cargo. Tente novamente.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            f"Cargo atualizado para **{role.name}**.", ephemeral=True
        )


class RoleIconModal(discord.ui.Modal):
    def __init__(self, cog, owner_id: int, role_id: int):
        self.cog = cog
        self.owner_id = owner_id
        self.role_id = role_id
        super().__init__(
            title="Editar ícone do cargo",
            custom_id=f"boost:icon:{owner_id}:{role_id}",
        )
        self.emoji_input = discord.ui.TextInput(
            label="Emoji",
            placeholder="Cole um emoji Unicode ou <:emoji:id>",
            max_length=100,
            required=True,
        )
        self.add_item(self.emoji_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "Esse formulário pertence a outra pessoa.", ephemeral=True
            )
        if not self.cog.is_booster(interaction.user):
            return await interaction.response.send_message(
                "Este comando é exclusivo para boosters.", ephemeral=True
            )

        role = interaction.guild.get_role(self.role_id)
        if role is None:
            return await interaction.response.send_message(
                "Não encontrei esse cargo no servidor.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            icon_png = await self.cog.emoji_to_png(self.emoji_input.value.strip())
            await role.edit(
                display_icon=icon_png,
                reason=f"Ícone personalizado solicitado por {interaction.user}",
            )
        except ValueError as error:
            return await interaction.followup.send(str(error), ephemeral=True)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return await interaction.followup.send(
                "Não consegui baixar a imagem do emoji. Tente novamente.",
                ephemeral=True,
            )
        except (UnidentifiedImageError, OSError):
            return await interaction.followup.send(
                "A imagem do emoji não pôde ser convertida para PNG.",
                ephemeral=True,
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                "Não tenho permissão para editar esse cargo. Confira também se o servidor permite ícones de cargos.",
                ephemeral=True,
            )
        except discord.HTTPException:
            return await interaction.followup.send(
                "O Discord não aceitou o ícone. Verifique se o servidor permite ícones de cargos e tente outro emoji.",
                ephemeral=True,
            )

        await interaction.followup.send(
            f"Ícone do cargo **{role.name}** atualizado.", ephemeral=True
        )


class FamilyMemberSelect(discord.ui.UserSelect):
    def __init__(self, cog, owner_id: int, adding: bool):
        self.cog = cog
        self.owner_id = owner_id
        self.adding = adding
        super().__init__(
            placeholder=(
                "Escolha quem adicionar"
                if adding
                else "Escolha quem remover"
            ),
            min_values=1,
            max_values=FAMILY_MEMBER_LIMIT,
            custom_id=f"boost:members:{owner_id}:{'add' if adding else 'remove'}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message(
                "Esse painel pertence a outra pessoa.", ephemeral=True
            )
        if not self.cog.is_booster(interaction.user):
            return await interaction.response.send_message(
                "Este comando é exclusivo para boosters.", ephemeral=True
            )

        state = self.cog.families.get(self.cog.key(interaction.guild_id, self.owner_id))
        role = interaction.guild.get_role(state["role_id"]) if state else None
        if role is None:
            return await interaction.response.send_message(
                "A família não está configurada. Use `,familia` para abrir o painel.",
                ephemeral=True,
            )

        chosen_members = [
            member
            for member in self.values
            if isinstance(member, discord.Member) and not member.bot
        ]
        current_members = set(role.members)

        if self.adding:
            new_members = [member for member in chosen_members if member not in current_members]
            if len(current_members) + len(new_members) > FAMILY_MEMBER_LIMIT:
                return await interaction.response.send_message(
                    f"A família pode ter no máximo {FAMILY_MEMBER_LIMIT} pessoas, contando você.",
                    ephemeral=True,
                )
            try:
                for member in new_members:
                    await member.add_roles(role, reason=f"Adicionado à família de {self.owner_id}")
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "Não consegui adicionar os membros. Verifique a hierarquia e as permissões do bot.",
                    ephemeral=True,
                )
            verb = "adicionado(s)"
        else:
            removable = [
                member
                for member in chosen_members
                if member in current_members and member.id != self.owner_id
            ]
            try:
                for member in removable:
                    await member.remove_roles(
                        role, reason=f"Removido da família de {self.owner_id}"
                    )
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "Não consegui remover os membros. Verifique a hierarquia e as permissões do bot.",
                    ephemeral=True,
                )
            verb = "removido(s)"

        changed_members = new_members if self.adding else removable
        if chosen_members and not changed_members:
            return await interaction.response.send_message(
                "Nenhum membro precisou ser alterado.", ephemeral=True
            )
        await interaction.response.send_message(
            f"{len(changed_members)} membro(s) {verb}.", ephemeral=True
        )


class Boost(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.storage_path = Path(__file__).resolve().parent.parent / "data" / "boost.json"
        self.families: dict[str, dict] = {}
        self.personal_roles: dict[str, int] = {}
        self.pool: asyncpg.Pool | None = None

    async def cog_load(self) -> None:
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.families = data.get("families", {})
                self.personal_roles = data.get("personal_roles", {})
            except (OSError, json.JSONDecodeError) as error:
                print(f"Não foi possível carregar os dados do boost: {error}")

        database_url = os.getenv("DATABASE") or os.getenv("DATABASE_URL")
        if not database_url:
            print("NeonDB indisponível para o cog boost: variável DATABASE não configurada.")
            return

        try:
            self.pool = await asyncpg.create_pool(
                dsn=database_url,
                ssl="require",
                min_size=1,
                max_size=5,
                command_timeout=20,
            )
            await self.pool.execute(
                """
                CREATE TABLE IF NOT EXISTS boost_role_owners (
                    guild_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    family_role_id BIGINT,
                    personal_role_id BIGINT,
                    voice_channel_id BIGINT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (guild_id, user_id)
                )
                """
            )
            await self.migrate_local_data()
            await self.load_database_data()
        except Exception as error:
            if self.pool is not None:
                await self.pool.close()
                self.pool = None
            print(
                "Não foi possível inicializar o NeonDB no cog boost: "
                f"{type(error).__name__}. Confira a variável DATABASE e os logs do Render."
            )
            return

        for key in self.families:
            guild_id, owner_id = map(int, key.split(":"))
            self.bot.add_view(self.family_view(guild_id, owner_id))
        for key in self.personal_roles:
            guild_id, owner_id = map(int, key.split(":"))
            self.bot.add_view(self.personal_view(guild_id, owner_id))

    async def cog_unload(self) -> None:
        if self.pool is not None:
            await self.pool.close()

    async def migrate_local_data(self) -> None:
        if self.pool is None:
            return

        for key in self.families.keys() | self.personal_roles.keys():
            guild_id, owner_id = map(int, key.split(":"))
            family = self.families.get(key, {})
            await self.pool.execute(
                """
                INSERT INTO boost_role_owners (
                    guild_id, user_id, family_role_id, personal_role_id,
                    voice_channel_id
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    family_role_id = COALESCE(
                        boost_role_owners.family_role_id, EXCLUDED.family_role_id
                    ),
                    personal_role_id = COALESCE(
                        boost_role_owners.personal_role_id, EXCLUDED.personal_role_id
                    ),
                    voice_channel_id = COALESCE(
                        boost_role_owners.voice_channel_id, EXCLUDED.voice_channel_id
                    ),
                    updated_at = NOW()
                """,
                guild_id,
                owner_id,
                family.get("role_id"),
                self.personal_roles.get(key),
                family.get("voice_channel_id"),
            )

    async def load_database_data(self) -> None:
        if self.pool is None:
            return

        self.families.clear()
        self.personal_roles.clear()
        rows = await self.pool.fetch(
            """
            SELECT guild_id, user_id, family_role_id, personal_role_id,
                   voice_channel_id
            FROM boost_role_owners
            """
        )
        for row in rows:
            key = self.key(row["guild_id"], row["user_id"])
            if row["family_role_id"] is not None:
                self.families[key] = {
                    "role_id": row["family_role_id"],
                    "voice_channel_id": row["voice_channel_id"],
                }
            if row["personal_role_id"] is not None:
                self.personal_roles[key] = row["personal_role_id"]

    def key(self, guild_id: int, owner_id: int) -> str:
        return f"{guild_id}:{owner_id}"

    def guild_id_for_role(self, role_id: int) -> int:
        for key, data in self.families.items():
            if data["role_id"] == role_id:
                return int(key.split(":")[0])
        for key, stored_role_id in self.personal_roles.items():
            if stored_role_id == role_id:
                return int(key.split(":")[0])
        return 0

    def is_booster(self, member: discord.abc.User) -> bool:
        return isinstance(member, discord.Member) and any(
            role.id == BOOSTER_ROLE_ID for role in member.roles
        )

    async def save(self) -> None:
        if self.pool is None:
            raise RuntimeError("NeonDB não está conectado.")

        records = []
        for key in self.families.keys() | self.personal_roles.keys():
            guild_id, owner_id = map(int, key.split(":"))
            family = self.families.get(key, {})
            records.append(
                (
                    guild_id,
                    owner_id,
                    family.get("role_id"),
                    self.personal_roles.get(key),
                    family.get("voice_channel_id"),
                )
            )

        if records:
            await self.pool.executemany(
                """
                INSERT INTO boost_role_owners (
                    guild_id, user_id, family_role_id, personal_role_id,
                    voice_channel_id
                )
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    family_role_id = EXCLUDED.family_role_id,
                    personal_role_id = EXCLUDED.personal_role_id,
                    voice_channel_id = EXCLUDED.voice_channel_id,
                    updated_at = NOW()
                """,
                records,
            )

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.storage_path.with_suffix(".tmp")
            temporary_path.write_text(
                json.dumps(
                    {"families": self.families, "personal_roles": self.personal_roles},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary_path.replace(self.storage_path)
        except OSError as error:
            print(f"Não foi possível atualizar o backup local do boost: {error}")

    async def repair_managed_roles(self, guild: discord.Guild) -> None:
        trigger_role = guild.get_role(REPAIR_BELOW_ROLE_ID)
        lower_role = guild.get_role(ROLE_POSITION_LOWER_ID)
        upper_role = guild.get_role(ROLE_POSITION_UPPER_ID)
        bot_member = guild.me
        if trigger_role is None or lower_role is None or upper_role is None:
            print(
                f"Não foi possível verificar cargos gerenciados em {guild.name}: "
                "cargo de referência não encontrado."
            )
            return
        if lower_role.position >= upper_role.position:
            print(
                f"Não foi possível mover cargos gerenciados em {guild.name}: "
                "os cargos de limite estão em ordem inválida."
            )
            return
        if bot_member is None or bot_member.top_role <= upper_role:
            print(
                f"Não foi possível mover cargos gerenciados em {guild.name}: "
                "o cargo do bot precisa estar acima do limite superior."
            )
            return

        managed_roles = sorted(
            (
                role
                for role in guild.roles
                if role.id not in {
                    REPAIR_BELOW_ROLE_ID,
                    ROLE_POSITION_LOWER_ID,
                    ROLE_POSITION_UPPER_ID,
                }
                and role.name.casefold().startswith(MANAGED_ROLE_PREFIXES)
                and role.position < trigger_role.position
            ),
            key=lambda role: role.position,
            reverse=True,
        )

        for role in managed_roles:
            if role >= bot_member.top_role:
                print(
                    f"Não foi possível mover o cargo {role.name!r} em {guild.name}: "
                    "ele está acima ou no mesmo nível do bot."
                )
                continue

            lower_role = guild.get_role(ROLE_POSITION_LOWER_ID)
            if lower_role is None:
                break
            target_position = lower_role.position + 1
            if role.position == target_position:
                continue

            try:
                await role.edit(
                    position=target_position,
                    reason="Corrigindo a posição de um cargo de booster",
                )
            except discord.Forbidden:
                print(
                    f"Sem permissão para mover o cargo {role.name!r} em {guild.name}."
                )
            except discord.HTTPException as error:
                print(
                    f"Falha ao mover o cargo {role.name!r} em {guild.name}: {error}"
                )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        for guild in self.bot.guilds:
            await self.repair_managed_roles(guild)

    async def create_managed_role(
        self, guild: discord.Guild, member: discord.Member, name_prefix: str
    ) -> discord.Role:
        lower_role = guild.get_role(ROLE_POSITION_LOWER_ID)
        upper_role = guild.get_role(ROLE_POSITION_UPPER_ID)
        bot_member = guild.me
        if lower_role is None or upper_role is None:
            raise ValueError("Não encontrei os cargos de referência configurados.")
        if lower_role.position >= upper_role.position:
            raise ValueError("Os cargos de referência estão em uma ordem inválida.")
        if bot_member is None or bot_member.top_role <= upper_role:
            raise ValueError(
                "Meu cargo precisa estar acima do cargo de referência superior."
            )

        role = await guild.create_role(
            name=f"{name_prefix} - {member.display_name}"[:100],
            reason=f"Cargo de booster criado para {member}",
        )
        try:
            await role.edit(
                position=lower_role.position + 1,
                reason="Posicionando o cargo de booster entre os cargos de referência",
            )
            await self.repair_managed_roles(guild)
        except Exception:
            await role.delete(reason="Não foi possível posicionar o cargo de booster")
            raise
        return role

    async def create_assigned_role(
        self,
        guild: discord.Guild,
        member: discord.Member,
        reason: str,
        name_prefix: str,
    ) -> discord.Role:
        role = await self.create_managed_role(guild, member, name_prefix)
        try:
            await member.add_roles(role, reason=reason)
        except Exception:
            try:
                await role.delete(reason="Não foi possível atribuir o cargo ao dono")
            except discord.HTTPException:
                pass
            raise
        return role

    def family_view(self, guild_id: int, owner_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        buttons = (
            ("Editar cargo", discord.ButtonStyle.primary, "edit"),
            ("Editar ícone", discord.ButtonStyle.secondary, "icon"),
            ("Criar call", discord.ButtonStyle.success, "voice"),
            ("Adicionar membros", discord.ButtonStyle.secondary, "add"),
            ("Remover membros", discord.ButtonStyle.secondary, "remove"),
        )
        for label, style, action in buttons:
            button = discord.ui.Button(
                label=label,
                style=style,
                custom_id=f"boost:family:{action}:{guild_id}:{owner_id}",
            )
            button.callback = self._family_callback(action, guild_id, owner_id)
            view.add_item(button)
        if self.personal_roles.get(self.key(guild_id, owner_id)):
            personal_button = discord.ui.Button(
                label="Editar cargo personalizado",
                style=discord.ButtonStyle.primary,
                custom_id=f"boost:family:personal-edit:{guild_id}:{owner_id}",
            )
            personal_button.callback = self._personal_edit_callback(
                guild_id, owner_id
            )
            view.add_item(personal_button)
        return view

    def personal_view(self, guild_id: int, owner_id: int) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        button = discord.ui.Button(
            label="Editar cargo",
            style=discord.ButtonStyle.primary,
            custom_id=f"boost:personal:edit:{guild_id}:{owner_id}",
        )
        button.callback = self._personal_edit_callback(guild_id, owner_id)
        view.add_item(button)
        icon_button = discord.ui.Button(
            label="Editar ícone",
            style=discord.ButtonStyle.secondary,
            custom_id=f"boost:personal:icon:{guild_id}:{owner_id}",
        )
        icon_button.callback = self._personal_icon_callback(guild_id, owner_id)
        view.add_item(icon_button)
        return view

    async def emoji_to_png(self, emoji_text: str) -> bytes:
        custom_emoji = re.fullmatch(
            r"<(?P<animated>a?):[A-Za-z0-9_]{2,32}:(?P<id>\d{15,22})>",
            emoji_text,
        )
        if custom_emoji:
            emoji_id = custom_emoji.group("id")
            extension = "gif" if custom_emoji.group("animated") else "png"
            url = (
                f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}?size=128"
            )
        else:
            if not emoji_text or len(emoji_text) > 16 or emoji_text.isspace():
                raise ValueError(
                    "Envie um único emoji Unicode ou emoji personalizado do Discord."
                )
            codepoints = "-".join(
                f"{ord(character):x}"
                for character in emoji_text
                if ord(character) not in {0xFE0E, 0xFE0F}
            )
            if not codepoints:
                raise ValueError("Não consegui identificar esse emoji.")
            url = (
                "https://cdn.jsdelivr.net/gh/jdecked/twemoji@latest/"
                f"assets/72x72/{codepoints}.png"
            )

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 404:
                    raise ValueError("Não encontrei a imagem desse emoji.")
                if response.status != 200:
                    raise ValueError("Não consegui baixar a imagem desse emoji.")
                image_data = await response.read()

        if len(image_data) > 8 * 1024 * 1024:
            raise ValueError("A imagem do emoji é grande demais.")

        with Image.open(BytesIO(image_data)) as source:
            image = source.convert("RGBA")
            image.thumbnail((64, 64), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format="PNG", optimize=True)
            return output.getvalue()

    def _family_callback(self, action: str, guild_id: int, owner_id: int):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != owner_id:
                return await interaction.response.send_message(
                    "Esse painel pertence a outra pessoa.", ephemeral=True
                )
            if not self.is_booster(interaction.user):
                return await interaction.response.send_message(
                    "Este comando é exclusivo para boosters.", ephemeral=True
                )
            if interaction.guild_id != guild_id:
                return await interaction.response.send_message(
                    "Esse painel não pertence a este servidor.", ephemeral=True
                )

            state = self.families.get(self.key(guild_id, owner_id))
            if state is None:
                return await interaction.response.send_message(
                    "Não encontrei os dados desta família. Use `,familia` novamente.",
                    ephemeral=True,
                )
            role = interaction.guild.get_role(state["role_id"])
            if role is None:
                return await interaction.response.send_message(
                    "O cargo da família não existe mais. Use `,familia` novamente.",
                    ephemeral=True,
                )

            if action == "edit":
                return await interaction.response.send_modal(
                    RoleEditModal(self, owner_id, role.id, family=True)
                )
            if action == "icon":
                return await interaction.response.send_modal(
                    RoleIconModal(self, owner_id, role.id)
                )
            if action in {"add", "remove"}:
                select_view = discord.ui.View(timeout=180)
                select_view.add_item(
                    FamilyMemberSelect(self, owner_id, adding=(action == "add"))
                )
                prompt = (
                    "Selecione as pessoas para adicionar à família."
                    if action == "add"
                    else "Selecione as pessoas para remover da família."
                )
                return await interaction.response.send_message(
                    prompt, view=select_view, ephemeral=True
                )

            if state.get("voice_channel_id"):
                voice_channel = interaction.guild.get_channel(state["voice_channel_id"])
                if voice_channel:
                    return await interaction.response.send_message(
                        f"A call exclusiva já está criada: {voice_channel.mention}",
                        ephemeral=True,
                    )
                state["voice_channel_id"] = None

            await interaction.response.defer()
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    view_channel=False, connect=False
                ),
                role: discord.PermissionOverwrite(
                    view_channel=True, connect=True, speak=True
                ),
            }
            try:
                voice_channel = await interaction.guild.create_voice_channel(
                    name=f"família-{interaction.user.display_name}"[:100],
                    overwrites=overwrites,
                    reason=f"Call exclusiva da família de {interaction.user}",
                )
            except discord.Forbidden:
                return await interaction.followup.send(
                    "Não tenho permissão para criar a call. Verifique `Gerenciar canais`.",
                    ephemeral=True,
                )
            except discord.HTTPException:
                return await interaction.followup.send(
                    "O Discord não conseguiu criar a call. Tente novamente.",
                    ephemeral=True,
                )

            state["voice_channel_id"] = voice_channel.id
            try:
                await self.save()
            except Exception:
                await interaction.message.edit(
                    embed=self.family_embed(interaction.guild, owner_id, state),
                    view=self.family_view(guild_id, owner_id),
                )
                return await interaction.followup.send(
                    f"Call criada: {voice_channel.mention}, mas não consegui salvar os dados no NeonDB.",
                    ephemeral=True,
                )
            await interaction.message.edit(
                embed=self.family_embed(interaction.guild, owner_id, state),
                view=self.family_view(guild_id, owner_id),
            )
            await interaction.followup.send(
                f"Call exclusiva criada: {voice_channel.mention}", ephemeral=True
            )

        return callback

    def _personal_edit_callback(self, guild_id: int, owner_id: int):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != owner_id:
                return await interaction.response.send_message(
                    "Esse painel pertence a outra pessoa.", ephemeral=True
                )
            if not self.is_booster(interaction.user):
                return await interaction.response.send_message(
                    "Este comando é exclusivo para boosters.", ephemeral=True
                )
            if interaction.guild_id != guild_id:
                return await interaction.response.send_message(
                    "Esse painel não pertence a este servidor.", ephemeral=True
                )
            role_id = self.personal_roles.get(self.key(guild_id, owner_id))
            role = interaction.guild.get_role(role_id) if role_id else None
            if role is None:
                return await interaction.response.send_message(
                    "Não encontrei seu cargo personalizado. Use `,cargo` novamente.",
                    ephemeral=True,
                )
            await interaction.response.send_modal(
                RoleEditModal(self, owner_id, role.id, family=False)
            )

        return callback

    def _personal_icon_callback(self, guild_id: int, owner_id: int):
        async def callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != owner_id:
                return await interaction.response.send_message(
                    "Esse painel pertence a outra pessoa.", ephemeral=True
                )
            if not self.is_booster(interaction.user):
                return await interaction.response.send_message(
                    "Este comando é exclusivo para boosters.", ephemeral=True
                )
            if interaction.guild_id != guild_id:
                return await interaction.response.send_message(
                    "Esse painel não pertence a este servidor.", ephemeral=True
                )
            role_id = self.personal_roles.get(self.key(guild_id, owner_id))
            role = interaction.guild.get_role(role_id) if role_id else None
            if role is None:
                return await interaction.response.send_message(
                    "Não encontrei seu cargo personalizado. Use `,cargo` novamente.",
                    ephemeral=True,
                )
            await interaction.response.send_modal(
                RoleIconModal(self, owner_id, role.id)
            )

        return callback

    def family_embed(
        self, guild: discord.Guild, owner_id: int, state: dict
    ) -> discord.Embed:
        role = guild.get_role(state["role_id"])
        voice_channel = guild.get_channel(state.get("voice_channel_id"))
        member_count = len(role.members) if role else 0
        embed = discord.Embed(
            title="Gerenciar família",
            description=(
                f"Cargo: {role.mention if role else 'não encontrado'}\n"
                f"Call: {voice_channel.mention if voice_channel else 'ainda não criada'}\n"
                f"Membros: {member_count}/{FAMILY_MEMBER_LIMIT}"
            ),
            color=role.color if role and role.color.value else discord.Color.blurple(),
        )
        personal_role_id = self.personal_roles.get(self.key(guild.id, owner_id))
        personal_role = guild.get_role(personal_role_id) if personal_role_id else None
        if personal_role is not None:
            embed.add_field(
                name="Cargo personalizado",
                value=(
                    f"{personal_role.mention}\n"
                    f"Cor: `#{personal_role.color.value:06X}`"
                ),
                inline=False,
            )
        embed.set_footer(text=f"Família de {guild.get_member(owner_id) or owner_id}")
        return embed

    def personal_role_embed(
        self, guild: discord.Guild, owner_id: int, role: discord.Role
    ) -> discord.Embed:
        embed = discord.Embed(
            title="Gerenciar cargo personalizado",
            description=(
                f"Cargo: {role.mention}\n"
                f"Cor: `#{role.color.value:06X}`"
            ),
            color=role.color if role.color.value else discord.Color.blurple(),
        )
        embed.set_footer(
            text=f"Cargo de {guild.get_member(owner_id) or owner_id}"
        )
        return embed

    @commands.command(name="familia")
    async def family_command(self, ctx: commands.Context) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return await ctx.send("Este comando só pode ser usado em um servidor.")
        if not self.is_booster(ctx.author):
            return await ctx.send("Este comando é exclusivo para boosters.")
        if self.pool is None:
            return await ctx.send(
                "Não consegui conectar ao NeonDB. Confira a variável `DATABASE` no Render."
            )

        key = self.key(ctx.guild.id, ctx.author.id)
        state = self.families.get(key)
        role = ctx.guild.get_role(state["role_id"]) if state else None
        if role is None:
            role = next(
                (
                    member_role
                    for member_role in ctx.author.roles
                    if member_role.name.casefold().startswith(("família -", "familia -"))
                ),
                None,
            )
            if role is not None:
                self.families[key] = {
                    "role_id": role.id,
                    "voice_channel_id": None,
                }
                try:
                    await self.save()
                except Exception:
                    return await ctx.send(
                        "Encontrei seu cargo de família, mas não consegui registrá-lo no NeonDB."
                    )

        state = self.families.get(key)
        if role is not None:
            return await ctx.send(
                embed=self.family_embed(ctx.guild, ctx.author.id, state),
                view=self.family_view(ctx.guild.id, ctx.author.id),
            )

        try:
            role = await self.create_assigned_role(
                ctx.guild,
                ctx.author,
                "Cargo da família do booster",
                "família",
            )
        except ValueError as error:
            return await ctx.send(str(error))
        except discord.Forbidden:
            return await ctx.send(
                "Não consegui criar ou atribuir o cargo. Confira minhas permissões e a hierarquia."
            )
        except discord.HTTPException:
            return await ctx.send("O Discord não conseguiu criar o cargo. Tente novamente.")

        self.families[key] = {"role_id": role.id, "voice_channel_id": None}
        try:
            await self.save()
        except Exception:
            self.families.pop(key, None)
            try:
                await role.delete(reason="Falha ao registrar a família no NeonDB")
            except discord.HTTPException:
                pass
            return await ctx.send(
                "Não consegui salvar sua família no NeonDB; o cargo criado foi removido."
            )
        self.bot.add_view(self.family_view(ctx.guild.id, ctx.author.id))
        state = self.families[key]
        await ctx.send(
            "Sua família foi criada. O cargo padrão já está com você; use os botões para editar, criar a call ou gerenciar membros.",
            embed=self.family_embed(ctx.guild, ctx.author.id, state),
            view=self.family_view(ctx.guild.id, ctx.author.id),
        )

    @commands.command(name="cargo")
    async def personal_role_command(self, ctx: commands.Context) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return await ctx.send("Este comando só pode ser usado em um servidor.")
        if not self.is_booster(ctx.author):
            return await ctx.send("Este comando é exclusivo para boosters.")
        if self.pool is None:
            return await ctx.send(
                "Não consegui conectar ao NeonDB. Confira a variável `DATABASE` no Render."
            )

        key = self.key(ctx.guild.id, ctx.author.id)
        role_id = self.personal_roles.get(key)
        role = ctx.guild.get_role(role_id) if role_id else None
        if role is None:
            role = next(
                (
                    member_role
                    for member_role in ctx.author.roles
                    if member_role.name.casefold().startswith("cargo -")
                ),
                None,
            )
            if role is not None:
                self.personal_roles[key] = role.id
                try:
                    await self.save()
                except Exception:
                    return await ctx.send(
                        "Encontrei seu cargo personalizado, mas não consegui registrá-lo no NeonDB."
                    )

        if role is None:
            try:
                role = await self.create_assigned_role(
                    ctx.guild,
                    ctx.author,
                    "Cargo personalizado do booster",
                    "cargo",
                )
            except ValueError as error:
                return await ctx.send(str(error))
            except discord.Forbidden:
                return await ctx.send(
                    "Não consegui criar ou atribuir o cargo. Confira minhas permissões e a hierarquia."
                )
            except discord.HTTPException:
                return await ctx.send("O Discord não conseguiu criar o cargo. Tente novamente.")
            self.personal_roles[key] = role.id
            try:
                await self.save()
            except Exception:
                self.personal_roles.pop(key, None)
                try:
                    await role.delete(reason="Falha ao registrar cargo pessoal no NeonDB")
                except discord.HTTPException:
                    pass
                return await ctx.send(
                    "Não consegui salvar seu cargo no NeonDB; o cargo criado foi removido."
                )
            self.bot.add_view(self.personal_view(ctx.guild.id, ctx.author.id))

        family = self.families.get(key)
        family_role = ctx.guild.get_role(family["role_id"]) if family else None
        if family_role is not None:
            return await ctx.send(
                embed=self.family_embed(ctx.guild, ctx.author.id, family),
                view=self.family_view(ctx.guild.id, ctx.author.id),
            )

        await ctx.send(
            embed=self.personal_role_embed(ctx.guild, ctx.author.id, role),
            view=self.personal_view(ctx.guild.id, ctx.author.id),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Boost(bot))