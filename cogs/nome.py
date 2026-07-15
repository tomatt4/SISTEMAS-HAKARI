import discord
from discord.ext import commands

GUILD_ID = 1500231901397516340
SUFIXO = "-tsuke"

class AutoNickname(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Ignora bots
        if member.bot:
            return

        # Só funciona no servidor definido
        if member.guild.id != GUILD_ID:
            return

        try:
            # Limite de 32 caracteres do Discord
            max_nome = 32 - len(SUFIXO)
            username = member.name[:max_nome]
            nickname = f"{username}{SUFIXO}"

            await member.edit(nick=nickname, reason="apelido automático ao entrar.")

        except discord.Forbidden:
            print(f"Sem permissão para alterar o apelido de {member}.")
        except discord.HTTPException as e:
            print(f"Erro ao alterar apelido de {member}: {e}")

async def setup(bot):
    await bot.add_cog(AutoNickname(bot))
