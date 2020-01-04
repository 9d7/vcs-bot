import discord
from discord.ext import commands
from src.base import *
import box
from typing import Optional

class NickError(CommandError):
    def __init__(self, message):
        super().__init__("nick")
        self.message = message


MAX_NICK_LEN = 32
MIN_NICK_LEN = 3

class NickCog(commands.Cog):

    def __init__(self, nick_file: str, bot):
        self.bot = bot
        with open(nick_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @staticmethod
    async def change_nick(user: discord.Member, nick: Optional[str]):
        if nick:
            if len(nick) > MAX_NICK_LEN:
                raise NickError("too_long")
            elif len(nick) < MIN_NICK_LEN:
                raise NickError("too_short")

        try:
            await user.edit(nick=nick)
        except Exception:
            raise NickError("forbidden")


    @commands.command()
    @commands.check(non_dm)
    @delete_source
    async def nick(self, ctx: commands.context, *args):
        if len(args) > 2:
            raise WrongArgLength("zero to two")

        if len(args) == 0:
            await self.change_nick(ctx.author, None)
            await send(ctx,
                       self.messages.reset,
                       tag=True, expire=True)
        elif len(args) == 1:
            nick = args[0]

            await self.change_nick(ctx.author, nick)
            await send(ctx,
                       self.messages.self_change.format(nick),
                       tag=True, expire=True)
        elif len(args) == 2:
            nick = args[1]
            user = find_user(ctx.guild, args[0])

            if not user:
                raise UserNotFound(args[0])

            await self.change_nick(user, nick)
            if user == ctx.author:
                await send(ctx,
                           self.messages.self_change.format(nick),
                           tag=True, expire=True)
                return

            await send(ctx,
                       self.messages.other_change.format(user.mention,
                                                         nick,
                                                         ctx.author.mention),
                       tag=False, expire=False)
