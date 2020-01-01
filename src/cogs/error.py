import discord
from discord.ext import commands
import sys
import traceback
from src.base import *
from src.cogs.poll import PollError
import box


# global error handler.
# modified from https://gist.github.com/EvieePy/7822af90858ef65012ea500bcecf1612
# prints all errors to a channel in the server.
class ErrorCog(commands.Cog):
    def __init__(self, error_file: str, bot):
        self.bot = bot
        with open(error_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound, commands.UserInputError)

        error = getattr(error, 'original', error)
        try:
            if isinstance(error, ignored):
                return

            elif isinstance(error, commands.DisabledCommand):
                return await send(ctx,
                                  self.messages.disabled.format(ctx.command),
                                  tag=True, expire=True)
            elif isinstance(error, commands.CheckFailure):
                return await send(ctx,
                                  self.messages.no_pm.format(ctx.command),
                                  tag=False, expire=True)
            elif isinstance(error, ArgIsNaN):
                return await send(ctx,
                                  self.messages.arg_is_nan.format(
                                      error.args[0]
                                  ), tag=True, expire=True)
            elif isinstance(error, PageOOB):
                return await send(ctx,
                                  self.messages.page_oob,
                                  tag=True, expire=True)
            elif isinstance(error, WrongArgLength):
                return await send(ctx,
                                  self.messages.wrong_arg_length.format(
                                      ctx.command, error.args[0]
                                  ), tag=True, expire=True)
            elif isinstance(error, PollError):
                return await send(ctx,
                                  self.messages.poll[error.args[0]],
                                  tag=True, expire=True)
        except Exception:
            pass
        print(PollError)
        print(type(error))

        exception_string = ctx.author.mention + "\n```" + \
                           "".join(traceback.format_exception(
                               type(error), error, error.__traceback__
                           )) + "```"
        if ctx.guild == None:
            await ctx.send(
                content=exception_string
            )
            return

        channel = None
        for possible_channel in ctx.guild.channels:
            if possible_channel.name == self.messages.error_channel:
                channel = possible_channel
                break

        if channel:
            await channel.send(exception_string)
