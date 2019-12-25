from discord.ext import commands
import discord
import psycopg2
from ruamel.yaml import YAML
from src.base import *

class PollCog(commands.Cog):

  def snowflake_to_str(self, flake: int):
    return "{0:016X}".format(flake)

  def __init__(self, poll_file: str, cursor, bot: commands.Bot):
    self.bot = bot
    self.cursor = cursor
    with open(poll_file, 'r') as msg_file:
      self.messages = YAML(typ='safe').load(msg_file)

  @commands.group()
  @delete_source
  async def poll(self, ctx: commands.context):
    if ctx.invoked_subcommand is None:
      await send(ctx, self.messages['command-not-found'], tag=True, expire=True)

  @poll.command()
  async def create(self, ctx: commands.context, *args):
    if len(args) == 0:
      await send(ctx, self.messages['wrong-arg-length'], tag=True, expire=True)
      return
    elif len(args) == 1:
      await send(ctx, "aaaaa", tag=True, expire=True)
    else:
      await send(ctx, "bbbbb", tag=True, expire=True)


  @poll.command()
  async def append(self, ctx: commands.context, *args):
    pass

  @poll.command()
  async def list(self, ctx: commands.context, *args):
    pass

  @poll.command()
  async def revive(self, ctx: commands.context, *args):
    pass

  @poll.command()
  async def view(self, ctx: commands.context, *args):
    pass

  @poll.command()
  async def purge(self, ctx: commands.context, *args):
    pass





