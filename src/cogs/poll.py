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
    poll_info = sql_request(cursor,
                            "SELECT Question, Username FROM Polls "
                            "WHERE PollID=%s;",
                            (poll_id,))[0]

    username = \
      guild.get_member(user_id=int(poll_info.username, base=16)).display_name

    # get option info
    options = sql_request(cursor,
                          "SELECT OptionID, Emoji, Option FROM Options "
                          "WHERE PollID = %s;", (poll_id,))

    print(options)

    # format strings
    header_string = style["poll-header"].format(poll_id,
                                                username)
    question_string = style["question-string"].format(poll_info.question)

    option_strings = []

    # get option readout
    for option in options:

      emoji = chr(int(option.emoji, base=16))

      # get votes
      users = sql_request(cursor,
                          "SELECT DISTINCT Username FROM Votes "
                          "WHERE OptionID=%s;",
                          (option.optionid,))

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
        vote_count, vote_str, emoji, option.option, all_votes)

      option_strings.append(final_string)

    # join string together :)
    return "\n".join([header_string, question_string, *option_strings])

  def snowflake_to_str(self, flake: int):
    return "{0:016X}".format(flake)

  ### REACTION HANDLERS
  ### Using on_raw_reaction_x here instead of on_reaction_x so that the bot
  ### will still process polls after a restart, when the internal cache is
  ### cleared.
  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    guild = self.bot.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = guild.get_member(payload.user_id)

    if (user == self.bot.user): return

    cursor = self.conn.cursor()

    # get poll
    cursor.execute("SELECT PollID FROM Polls WHERE Message=%s AND Channel=%s;",
                   (self.snowflake_to_str(payload.message_id),
                    self.snowflake_to_str(payload.channel_id)))

    try:
      poll = cursor.fetchone()
      if not poll: return
    except psycopg2.ProgrammingError:
      await channel.send(content=
                         self.messages["errors"]["critical-database-issue"])
      return

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

  # TODO: Remove this when done
  @poll.command()
  async def reset(self, ctx: commands.context, *args):
    cursor = self.conn.cursor()

    cursor.execute("DELETE FROM Polls; "
                   "DELETE FROM Options;"
                   "DELETE FROM Votes;"
                   "ALTER SEQUENCE Polls_PollID_seq RESTART;"
                   "ALTER SEQUENCE Options_OptionID_seq RESTART;")
