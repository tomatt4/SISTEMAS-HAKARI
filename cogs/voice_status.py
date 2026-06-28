import discord
from discord.ext import commands, tasks

VOICE_CHANNEL_ID = 1512845054450991115

class VoiceStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.keep_voice.start()

    def cog_unload(self):
        self.keep_voice.cancel()

    @tasks.loop(seconds=30)
    async def keep_voice(self):
        channel = self.bot.get_channel(VOICE_CHANNEL_ID)

        if channel is None:
            return

        guild = channel.guild
        voice_client = guild.voice_client

        try:
            if voice_client is None:
                await channel.connect(self_deaf=True)
                print(f"Conectado ao canal de voz: {channel.name}")

            elif voice_client.channel.id != VOICE_CHANNEL_ID:
                await voice_client.move_to(channel)
                print(f"Movido de volta para: {channel.name}")

        except Exception as e:
            print(f"Erro ao conectar na call: {e}")

    @keep_voice.before_loop
    async def before_keep_voice(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(VoiceStatus(bot))
