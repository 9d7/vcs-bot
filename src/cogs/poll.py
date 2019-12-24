from discord.ext import commands
import discord
import psycopg2
from ruamel.yaml import YAML
import datetime
import box
from contextlib import suppress
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






