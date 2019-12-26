from discord.ext import commands
import discord
import psycopg2
from ruamel.yaml import YAML
from src.base import *
from datetime import datetime


class PollCog(commands.Cog):

  def __init__(self, poll_file: str,
               conn, bot: commands.Bot):
    self.bot = bot
    self.conn = conn
    with open(poll_file, 'r') as msg_file:
      self.messages = YAML(typ='safe').load(msg_file)

  def get_poll_string(self, guild: discord.Guild, poll_id):

    style = self.messages["style"]
    errors = self.messages["errors"]

    cursor = self.conn.cursor()

    # get poll info
    cursor.execute("SELECT Question, Username FROM Polls "
                   "WHERE PollID=%s;", (poll_id,))

    try:
      cursor_ret = cursor.fetchone()

      # get poll string of nonexistent poll. should never happen
      if not cursor_ret:
        return errors["poll-not-found-critical"]

      question, user = cursor_ret

    except psycopg2.ProgrammingError:
      return errors["critical-database-issue"]

    username = guild.get_member(user_id=int(user, base=16)).display_name

    # get option info
    cursor.execute("SELECT OptionID, Emoji, Option FROM Options "
                   "WHERE PollID = %s;", (poll_id,))

    try:
      # wrap into dictionaries for readability
      option_desc = [field.name for field in cursor.description]
      options = [dict(zip(option_desc, option)) for option in cursor.fetchall()]

      if options == []:
        return errors["options-not-found"]

    except psycopg2.ProgrammingError:
      return errors["critical-database-issue"]

    # format strings
    header_string = style["poll-header"].format(poll_id,
                                                username)
    question_string = style["question-string"].format(question)

    option_strings = []

    # get option readout
    for option in options:
      emoji = chr(int(option['emoji'], base=16))


      # get votes
      cursor.execute("SELECT DISTINCT Username FROM Votes "
                     "WHERE OptionID=%s;", (option["optionid"],))
      try:
        all = cursor.fetchall()
        users = [i[0] for i in cursor.fetchall()]

      except psycopg2.ProgrammingError:
        return errors["critical-database-issue"]

      all_votes = ", ".join(
        guild.get_member(user_id=int(voter_id, 16)).display_name
        for voter_id in users)

      if all_votes == "":
        all_votes = style["no-votes"]

      # format options string
      vote_count = len(users)

      vote_str = style["vote-plural"]
      if vote_count == 1:
        vote_str = style["vote-singular"]

      final_string = style["option-string"].format(
        vote_count, vote_str, emoji, option["option"], all_votes)

      option_strings.append(final_string)

    # join string together :)
    return "\n".join([header_string, question_string, *option_strings])

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

    cursor = self.conn.cursor()

    cursor.execute("INSERT INTO Polls "
                   "(Question, Username, Time, "
                   "LastUpdate, Message, Channel) "
                   "VALUES (%s, %s, %s, %s, %s, %s) RETURNING PollID;",
                   (question, user_flake, datetime.now(),
                    datetime.now(), message_flake, channel_flake))

    poll_id = cursor.fetchone()[0]

    if len(args) == 1:
      options = zip(self.messages['default_poll']['options'],
                    self.messages['default_poll']['emojis'])
    else:
      options = zip(args[1:],
                    self.messages['emojis'])

    for option, emoji in options:
      cursor.execute("INSERT INTO Options "
                     "(PollID, Original, Username, Emoji, Option) "
                     "VALUES (%s, %s, %s, %s, %s);",
                     (poll_id, True, user_flake, emoji, option))
      await message.add_reaction(chr(int(emoji, 16)))

    message_string = self.get_poll_string(ctx.guild, poll_id)

    await message.edit(content=message_string)

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
