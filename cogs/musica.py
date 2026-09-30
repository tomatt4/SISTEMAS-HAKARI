import asyncio
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import discord
import imageio_ffmpeg
import yt_dlp
from discord import app_commands
from discord.ext import commands


YTDL_OPTIONS = {
    'format': 'bestaudio/best/ba*/b',
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    'source_address': '0.0.0.0',

    "extractor_args": {
        "youtube": {
            "player_client": 'player_client': ['ios', 'android', 'mweb'],
        },
    },
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


@contextmanager
def youtube_dl_instance():
    options = YTDL_OPTIONS.copy()
    cookie_file = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
    temporary_cookie_file = None

    try:
        if cookie_file:
            source_cookie_file = Path(cookie_file)
            if not source_cookie_file.is_file():
                raise FileNotFoundError(
                    "O arquivo configurado em YOUTUBE_COOKIES_FILE não existe."
                )

            with tempfile.NamedTemporaryFile(
                prefix="youtube-cookies-",
                suffix=".txt",
                delete=False,
            ) as temporary_file:
                temporary_cookie_file = Path(temporary_file.name)
                temporary_file.write(source_cookie_file.read_bytes())

            options["cookiefile"] = str(temporary_cookie_file)

        with yt_dlp.YoutubeDL(options) as ytdl:
            yield ytdl
    finally:
        if temporary_cookie_file:
            temporary_cookie_file.unlink(missing_ok=True)


def describe_youtube_error(error: Exception) -> str:
    message = str(error)
    normalized_message = message.lower().replace("’", "'")

    if "confirm you're not a bot" in normalized_message:
        cookie_file = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
        if not cookie_file:
            return (
                "O YouTube exigiu autenticação, mas YOUTUBE_COOKIES_FILE "
                "não está definida no processo do bot. Configure no Render "
                "o caminho de um Secret File em formato Netscape e reinicie."
            )
        if not Path(cookie_file).is_file():
            return (
                "YOUTUBE_COOKIES_FILE está definida, mas o arquivo não foi "
                "encontrado no servidor. Confira o Secret File e o caminho."
            )
        return (
            "O arquivo de cookies foi encontrado, mas o YouTube ainda os "
            "recusou. Exporte cookies Netscape recentes de uma sessão "
            "conectada ao YouTube e atualize o Secret File no Render."
        )

    if isinstance(error, FileNotFoundError):
        return (
            "O arquivo de cookies configurado não foi encontrado no servidor. "
            "Confira o caminho de YOUTUBE_COOKIES_FILE."
        )

    return message


@dataclass
class Track:
    title: str
    url: str
    requested_by: str
    text_channel_id: int


@dataclass
class MusicState:
    queue: list[Track] = field(default_factory=list)
    current: Track | None = None
    worker: asyncio.Task | None = None
    generation: int = 0


def extract_track(query: str) -> Track:
    with youtube_dl_instance() as ytdl:
        result = ytdl.extract_info(query, download=False)

    if result is None:
        raise ValueError("Não encontrei essa música.")

    if "entries" in result:
        result = next(
            (entry for entry in result["entries"] if entry is not None),
            None,
        )

    if result is None:
        raise ValueError("Não encontrei resultados para essa busca.")

    webpage_url = result.get("webpage_url") or result.get("original_url")
    if not webpage_url:
        raise ValueError("Não consegui obter o link dessa música.")

    return Track(
        title=result.get("title") or "Música sem título",
        url=webpage_url,
        requested_by="",
        text_channel_id=0,
    )


def extract_audio_url(url: str) -> str:
    with youtube_dl_instance() as ytdl:
        result = ytdl.extract_info(url, download=False)

    if result is None:
        raise ValueError("Não foi possível abrir o áudio.")

    if "entries" in result:
        result = next(
            (entry for entry in result["entries"] if entry is not None),
            None,
        )

    audio_url = result.get("url") if result else None
    if not audio_url:
        raise ValueError("O YouTube não retornou um endereço de áudio.")

    return audio_url


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, MusicState] = {}

    async def _get_requester_voice(
        self,
        interaction: discord.Interaction,
    ) -> discord.VoiceClient | None:
        if interaction.guild is None or not isinstance(
            interaction.user, discord.Member
        ):
            await interaction.response.send_message(
                "Esse comando só funciona dentro de um servidor.",
                ephemeral=True,
            )
            return None

        if interaction.user.voice is None or interaction.user.voice.channel is None:
            await interaction.response.send_message(
                "Entre em um canal de voz primeiro.",
                ephemeral=True,
            )
            return None

        voice = interaction.guild.voice_client
        if voice is None:
            await interaction.response.send_message(
                "Não estou em um canal de voz.",
                ephemeral=True,
            )
            return None
        elif voice.channel != interaction.user.voice.channel:
            await interaction.response.send_message(
                "Você precisa estar no mesmo canal de voz que eu.",
                ephemeral=True,
            )
            return None

        return voice

    def _state_for(self, guild_id: int) -> MusicState:
        return self.states.setdefault(guild_id, MusicState())

    async def _play_queue(self, guild: discord.Guild, state: MusicState) -> None:
        while state.queue:
            voice = guild.voice_client
            if voice is None or not voice.is_connected():
                break

            generation = state.generation
            track = state.queue.pop(0)
            state.current = track
            channel = self.bot.get_channel(track.text_channel_id)

            try:
                audio_url = await asyncio.to_thread(extract_audio_url, track.url)
                if generation != state.generation:
                    continue

                source = discord.FFmpegPCMAudio(
                    audio_url,
                    executable=imageio_ffmpeg.get_ffmpeg_exe(),
                    before_options=FFMPEG_BEFORE_OPTIONS,
                    options="-vn",
                )
                finished = asyncio.Event()

                def after(error: Exception | None) -> None:
                    if error:
                        print(f"Erro ao reproduzir áudio: {error}", flush=True)
                    self.bot.loop.call_soon_threadsafe(finished.set)

                voice.play(source, after=after)
                if channel:
                    await channel.send(f"▶️ Tocando agora: **{track.title}**")
                await finished.wait()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                print(
                    f"Erro ao reproduzir '{track.title}': {error}",
                    flush=True,
                )
                if channel:
                    await channel.send(
                        f"Não consegui reproduzir **{track.title}**. "
                        f"{describe_youtube_error(error)}"
                    )
            finally:
                state.current = None

        if not state.queue:
            state.worker = None

    @app_commands.command(name="play", description="Toca uma música do YouTube")
    @app_commands.describe(busca="Link do YouTube ou nome da música")
    async def play(self, interaction: discord.Interaction, busca: str) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Esse comando só funciona dentro de um servidor.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member) or interaction.user.voice is None:
            await interaction.response.send_message(
                "Entre em um canal de voz primeiro.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        try:
            track = await asyncio.to_thread(extract_track, busca)
        except Exception as error:
            await interaction.followup.send(
                f"Não encontrei essa música: {describe_youtube_error(error)}"
            )
            return

        try:
            voice = interaction.guild.voice_client
            if voice is None:
                voice = await interaction.user.voice.channel.connect()
            elif voice.channel != interaction.user.voice.channel:
                await interaction.followup.send(
                    "Você precisa estar no mesmo canal de voz que eu."
                )
                return
        except (discord.ClientException, discord.HTTPException) as error:
            await interaction.followup.send(f"Não consegui entrar no canal: {error}")
            return

        track.requested_by = interaction.user.display_name
        track.text_channel_id = interaction.channel_id
        state = self._state_for(interaction.guild.id)
        state.queue.append(track)

        if state.worker is None or state.worker.done():
            state.worker = asyncio.create_task(self._play_queue(interaction.guild, state))
            message = f"🔎 Adicionada à fila: **{track.title}**"
        else:
            message = f"➕ Adicionada à fila: **{track.title}**"

        await interaction.followup.send(message)

    @app_commands.command(name="pause", description="Pausa a música atual")
    async def pause(self, interaction: discord.Interaction) -> None:
        voice = await self._get_requester_voice(interaction)
        if voice is None:
            return
        if not voice.is_playing():
            await interaction.response.send_message("Não há música tocando.", ephemeral=True)
            return
        voice.pause()
        await interaction.response.send_message("⏸️ Música pausada.")

    @app_commands.command(name="resume", description="Retoma a música pausada")
    async def resume(self, interaction: discord.Interaction) -> None:
        voice = await self._get_requester_voice(interaction)
        if voice is None:
            return
        if not voice.is_paused():
            await interaction.response.send_message("A música não está pausada.", ephemeral=True)
            return
        voice.resume()
        await interaction.response.send_message("▶️ Música retomada.")

    @app_commands.command(name="skip", description="Pula para a próxima música")
    async def skip(self, interaction: discord.Interaction) -> None:
        voice = await self._get_requester_voice(interaction)
        if voice is None:
            return
        if not voice.is_playing() and not voice.is_paused():
            await interaction.response.send_message("Não há música tocando.", ephemeral=True)
            return
        voice.stop()
        await interaction.response.send_message("⏭️ Música pulada.")

    @app_commands.command(name="stop", description="Para a música e limpa a fila")
    async def stop(self, interaction: discord.Interaction) -> None:
        voice = await self._get_requester_voice(interaction)
        if voice is None:
            return
        state = self._state_for(interaction.guild.id)
        state.queue.clear()
        state.current = None
        state.generation += 1
        if voice.is_playing() or voice.is_paused():
            voice.stop()
        await interaction.response.send_message("⏹️ Reprodução parada e fila limpa.")

    @app_commands.command(name="queue", description="Mostra a fila de músicas")
    async def queue(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message(
                "Esse comando só funciona dentro de um servidor.",
                ephemeral=True,
            )
            return

        state = self.states.get(interaction.guild.id)
        if state is None or (state.current is None and not state.queue):
            await interaction.response.send_message("A fila está vazia.")
            return

        lines = []
        if state.current:
            lines.append(f"▶️ Tocando: **{state.current.title}**")
        lines.extend(
            f"{index}. {track.title} (pedido por {track.requested_by})"
            for index, track in enumerate(state.queue, start=1)
        )
        await interaction.response.send_message("\n".join(lines)[:1900])

    @app_commands.command(name="leave", description="Desconecta do canal de voz")
    async def leave(self, interaction: discord.Interaction) -> None:
        voice = await self._get_requester_voice(interaction)
        if voice is None:
            return

        state = self.states.pop(interaction.guild.id, None)
        if state:
            state.queue.clear()
            if state.worker and not state.worker.done():
                state.worker.cancel()
        voice.stop()
        await voice.disconnect()
        await interaction.response.send_message("Desconectado do canal de voz.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))