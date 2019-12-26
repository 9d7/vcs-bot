from discord.ext import commands
import discord
import psycopg2
from ruamel.yaml import YAML
from src.base import *
from datetime import datetime


class PollCog(commands.Cog):

  def __init__(self, poll_file: str, cursor, bot: commands.Bot):
    self.bot = bot
    self.cursor = cursor
    with open(poll_file, 'r') as msg_file:
      self.messages = YAML(typ='safe').load(msg_file)

  def get_poll_string(self, poll_id):
    return "Testing. Will work shortly!"

  def snowflake_to_str(self, flake: int):
    return "{0:016X}".format(flake)

  @commands.group()
  @delete_source
  async def poll(self, ctx: commands.context):
    if ctx.invoked_subcommand is None:
      await send(ctx, self.messages['errors']['command-not-found'],
                 tag=True, expire=True)

  @poll.command()
  async def create(self, ctx: commands.context, *args):
    if len(args) == 0:
      await send(ctx, self.messages['errors']['wrong-arg-length'],
                 tag=True, expire=True)
      return

    message = await send(ctx, self.messages['messages']['loading'],
                         tag=False, expire=False)

    message_flake = self.snowflake_to_str(message.id)
    channel_flake = self.snowflake_to_str(ctx.channel.id)
    user_flake = self.snowflake_to_str(ctx.author.id)
    question = args[0]

    self.cursor.execute("INSERT INTO Polls "
                        "(Question, Username, Time, "
                        "LastUpdate, Message, Channel) "
                        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING PollID;",
                        (question, user_flake, datetime.now(),
                         datetime.now(), message_flake, channel_flake))

    poll_id = self.cursor.fetchone()[0]

    if len(args) == 1:
      options = zip(self.messages['default_poll']['options'],
                    self.messages['default_poll']['emojis'])
    else:
      options = zip(args[1:],
                    self.messages['emojis'])

    for option in options:
      self.cursor.execute("INSERT INTO Options "
                          "(PollID, Original, Username, Emoji, Option) "
                          "VALUES (%s, %s, %s, %s, %s);",
                          (poll_id, True, user_flake, option[1], option[0]))

    message_string = self.get_poll_string(poll_id)



    header = self.messages['style']['poll-header'].format(0, ctx.author.name)
    q_str = self.messages['style']['question-string'].format(question)

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
