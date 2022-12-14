# -*- coding: utf-8 -*-

from discord.ext import commands
import discord
import asyncio
import youtube_dl

youtube_dl.utils.bug_reports_message = lambda: ''  # Suppress noise about console usage from errors

ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0"  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    "options": "-vn"
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data["entries"][0]

        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    """TODO: The description for Music goes here."""
    # TODO: music queue, loop, now playing, play list, stabilize stream

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @commands.command()
    async def slowplay(self, ctx, *, url):
        """Plays from a url (almost anything youtube_dl supports). Use !stream for playlists!"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(player, after=lambda e: print("Lej??tsz?? hiba: %s" % e) if e else None)

        await ctx.send("Jelenleg lej??tsz??s alatt(**/2/**): {}".format(player.title))

    @commands.command()
    async def play(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload). Can be unstable"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Hiba: %s' % e) if e else None)

        await ctx.send("Jelenleg lej??tsz??s alatt: {}".format(player.title))

    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Nem vagy hangcsatorn??ban.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Hanger?? m??dos??tva erre: {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @slowplay.before_invoke
    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Nem vagy hangcsatorn??ban.")
                raise commands.CommandError("nem csatlakozott hangcsatorn??hoz.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


def setup(bot: commands.Bot):
    bot.add_cog(Music(bot))
