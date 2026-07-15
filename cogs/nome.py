import discord
from discord.ext import commands

GUILD_ID = 1500231901397516340  # ID do servidor
SUFIXO = "-tsuke"

class AutoNickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def aplicar_sufixo(self, member: discord.Member):
        # Ignora bots
        if member.bot:
            return

        # Nome atual (apelido ou username)
        nome_atual = member.nick or member.name

        # Já possui o sufixo
        if nome_atual.endswith(SUFIXO):
            return

        # Respeita o limite de 32 caracteres
        max_nome = 32 - len(SUFIXO)
        novo_nome = f"{nome_atual[:max_nome]}{SUFIXO}"

        try:
            await member.edit(
                nick=novo_nome,
                reason="Aplicação automática de sufixo."
            )
        except (discord.Forbidden, discord.HTTPException):
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return

        print(f"Verificando apelidos em {guild.name}...")

        for member in guild.members:
            await self.aplicar_sufixo(member)

        print("Verificação concluída!")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != GUILD_ID:
            return

        await self.aplicar_sufixo(member)

async def setup(bot):
    await bot.add_cog(AutoNickname(bot))
