from src.tex2png import tex2png

import discord
from discord.ext import commands
from src.base import *
import box
import time, os

class MathError(CommandError):
    def __init__(self, message):
        super().__init__("math")
        self.message = message

class MathCog(commands.Cog):

    def __init__(self, math_file: str, bot):

        self.bot = bot
        with open(math_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @commands.command()
    @delete_source
    async def math(self, ctx: commands.context, *, snippet: str):

        photo_id = f"snippet{int(time.time() * 1000)}"

        res = tex2png(snippet,
                      debug=False,
                      density=500,
                      background="Transparent",
                      foreground="rgb 1.0 1.0 1.0",
                      outfile=photo_id,
                      latex='/app/.apt/usr/bin/latex',
                      dvipng='/app/.apt/usr/bin/dvipng'
                      )

        if res > 0:
            raise MathError("dependencies_missing")
        if res < 0:
            raise MathError("invalid")

        await ctx.send(content=self.messages.header.format(ctx.author.mention),
                       file=discord.File(photo_id + ".png"))

        os.remove(photo_id + ".png")
