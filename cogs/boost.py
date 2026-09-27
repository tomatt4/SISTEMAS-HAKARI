import json
import re
from pathlib import Path

import discord
from discord.ext import commands


BOOSTER_ROLE_ID = 1553817043076259911
LOWER_ROLE_ID = 1553840737655988244
UPPER_ROLE_ID = 1553842552237457510
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

    async def cog_load(self) -> None:
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.families = data.get("families", {})
                self.personal_roles = data.get("personal_roles", {})
            except (OSError, json.JSONDecodeError) as error:
                print(f"Não foi possível carregar os dados do boost: {error}")

        for key in self.families:
            guild_id, owner_id = map(int, key.split(":"))
            self.bot.add_view(self.family_view(guild_id, owner_id))
        for key in self.personal_roles:
            guild_id, owner_id = map(int, key.split(":"))
            self.bot.add_view(self.personal_view(guild_id, owner_id))

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

    async def create_managed_role(
        self, guild: discord.Guild, member: discord.Member
    ) -> discord.Role:
        lower_role = guild.get_role(LOWER_ROLE_ID)
        upper_role = guild.get_role(UPPER_ROLE_ID)
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
            name=f"família - {member.display_name}"[:100],
            reason=f"Cargo de booster criado para {member}",
        )
        try:
            await role.edit(
                position=lower_role.position + 1,
                reason="Posicionando o cargo de booster entre os cargos de referência",
            )
        except Exception:
            await role.delete(reason="Não foi possível posicionar o cargo de booster")
            raise
        return role

    async def create_assigned_role(
        self, guild: discord.Guild, member: discord.Member, reason: str
    ) -> discord.Role:
        role = await self.create_managed_role(guild, member)
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
        return view

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
            await self.save()
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
        embed.set_footer(text=f"Família de {guild.get_member(owner_id) or owner_id}")
        return embed

    @commands.command(name="familia")
    async def family_command(self, ctx: commands.Context) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member):
            return await ctx.send("Este comando só pode ser usado em um servidor.")
        if not self.is_booster(ctx.author):
            return await ctx.send("Este comando é exclusivo para boosters.")

        key = self.key(ctx.guild.id, ctx.author.id)
        state = self.families.get(key)
        if state and ctx.guild.get_role(state["role_id"]):
            return await ctx.send(
                embed=self.family_embed(ctx.guild, ctx.author.id, state),
                view=self.family_view(ctx.guild.id, ctx.author.id),
            )

        try:
            role = await self.create_assigned_role(
                ctx.guild, ctx.author, "Cargo da família do booster"
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
        await self.save()
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

        key = self.key(ctx.guild.id, ctx.author.id)
        role_id = self.personal_roles.get(key)
        role = ctx.guild.get_role(role_id) if role_id else None
        if role is None:
            try:
                role = await self.create_assigned_role(
                    ctx.guild, ctx.author, "Cargo personalizado do booster"
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
            await self.save()
            self.bot.add_view(self.personal_view(ctx.guild.id, ctx.author.id))

        await ctx.send(
            f"Seu cargo personalizado: {role.mention}. Clique para editar o nome e a cor.",
            view=self.personal_view(ctx.guild.id, ctx.author.id),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Boost(bot))