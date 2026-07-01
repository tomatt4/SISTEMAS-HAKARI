import discord
from discord.ext import commands, tasks

VOICE_CHANNEL_ID = 1520828048075788308

class VoiceStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.keep_voice.start()

    def cog_unload(self):
        self.keep_voice.cancel()

    @tasks.loop(minutes=2)
    async def keep_voice(self):
        channel = self.bot.get_channel(VOICE_CHANNEL_ID)

        if not isinstance(channel, discord.VoiceChannel):
            print("Canal de voz não encontrado ou ID inválido.")
            return

        guild = channel.guild
        vc = guild.voice_client

        try:
            if vc is None or not vc.is_connected():
                print(f"[VOICE] Conectando em {channel.name}")
                await channel.connect(self_deaf=True, reconnect=True, timeout=30)
                return

            if vc.channel and vc.channel.id != VOICE_CHANNEL_ID:
                print(f"[VOICE] Movendo para {channel.name}")
                await vc.move_to(channel)

        except discord.ClientException as e:
            print(f"[VOICE] ClientException: {e}")

        except discord.Forbidden:
            print("[VOICE] Sem permissão pra conectar.")

        except Exception as e:
            print(f"[VOICE] Erro: {type(e).__name__}: {e}")

    @keep_voice.before_loop
    async def before_keep_voice(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(VoiceStatus(bot))
