from __future__ import annotations

import discord
from discord.ext import commands


class UserInfo(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.hybrid_command(
        name="userinfo",
        description="Mostra informacoes do perfil de um usuario.",
    )
    @commands.guild_only()
    async def user_info(
        self,
        ctx: commands.Context[commands.Bot],
        member: discord.Member | None = None,
    ) -> None:
        target = member or ctx.author

        fetched_user = await self.bot.fetch_user(target.id)
        joined_at = (
            discord.utils.format_dt(target.joined_at, style="F")
            if target.joined_at
            else "Nao disponivel"
        )
        banner_url = fetched_user.banner.url if fetched_user.banner else None

        embed = discord.Embed(
            title=f"Perfil de {target}",
            color=target.color if target.color.value else discord.Color.blue(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        embed.add_field(name="Nome de usuario", value=str(target), inline=True)
        embed.add_field(name="Nome exibido", value=target.display_name, inline=True)
        embed.add_field(name="ID", value=str(target.id), inline=True)
        embed.add_field(
            name="Conta criada em",
            value=discord.utils.format_dt(target.created_at, style="F"),
            inline=False,
        )
        embed.add_field(name="Entrou no servidor em", value=joined_at, inline=False)
        embed.add_field(name="Bot?", value="Sim" if target.bot else "Nao", inline=True)
        embed.add_field(name="Cargo principal", value=target.top_role.mention, inline=True)

        roles = [role.mention for role in target.roles if role != ctx.guild.default_role]
        roles_text = ", ".join(roles[:15]) if roles else "Nenhum cargo alem do padrao"
        if len(roles) > 15:
            roles_text = f"{roles_text} e mais {len(roles) - 15} cargo(s)"

        embed.add_field(
            name="Cargos",
            value=roles_text,
            inline=False,
        )

        if banner_url:
            embed.set_image(url=banner_url)

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UserInfo(bot))
