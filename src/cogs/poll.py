from discord.ext import commands
import discord
import psycopg2
from ruamel.yaml import YAML
from src.base import *
from datetime import datetime
import box

MAX_QUESTION_LENGTH = 255
MAX_OPTION_LENGTH = 80


class PollCog(commands.Cog):

  def __init__(self, poll_file: str,
               conn, bot: commands.Bot):
    self.bot = bot
    self.conn = conn
    with open(poll_file, 'r') as msg_file:
      self.messages = box.Box.from_yaml(msg_file)

  def emoji_to_str(self, flake: str):
    return "{0:08X}".format(ord(flake))

  def str_to_emoji(self, emoji: str):
    return chr(int(emoji, base=16))

  def snowflake_to_str(self, flake: int):
    return "{0:016X}".format(flake)

  def str_to_snowflake(self, flake: str):
    return int(flake, 16)

  def get_poll_string(self, guild: discord.Guild, poll_id):

    style = self.messages.style
    errors = self.messages.errors

    cursor = self.conn.cursor()

    # get poll info
    poll_info = sql_request(cursor,
                            "SELECT Question, Username FROM Polls "
                            "WHERE PollID=%s;",
                            (poll_id,))[0]

    username = guild.get_member(
      user_id=self.str_to_snowflake(poll_info.username)).display_name

    # get option info, ordered from most to fewest votes
    options = sql_request(cursor,
                          "SELECT MAX(O.OptionID) AS OptionID, "
                          "       MAX(Emoji) AS Emoji, "
                          "       MAX(Option) AS Option "
                          "FROM Options AS O "
                          "LEFT OUTER JOIN Votes AS V "
                          "ON O.OptionID=V.OptionID "
                          "WHERE O.PollID=%s "
                          "GROUP BY O.OptionID "
                          "ORDER BY "
                          "  COUNT(V.Username) DESC, "
                          "  OptionID ASC;", (poll_id,))

    # format strings
    header_string = style.poll_header.format(poll_id,
                                                username)
    question_string = style.question_string.format(poll_info.question)

    option_strings = []

    # get option readout
    for option in options:

      emoji = self.str_to_emoji(option.emoji)

      # get votes
      users = sql_request(cursor,
                          "SELECT DISTINCT Username FROM Votes "
                          "WHERE OptionID=%s;",
                          (option.optionid,))

      all_votes = ", ".join(
        guild.get_member(user_id=self.str_to_snowflake(voter_id)).display_name
        for voter_id in users)

      if all_votes == "":
        all_votes = style.no_votes

      # format options string
      vote_count = len(users)

      vote_str = style.vote_plural
      if vote_count == 1:
        vote_str = style.vote_singular

      final_string = style.option_string.format(
        vote_count, vote_str, emoji, option.option, all_votes)

      option_strings.append(final_string)

    # join string together :)
    ret = "\n".join([header_string, question_string, *option_strings])
    if len(ret) >= MAX_TEXT_LENGTH:
      return errors.poll_overflow

    return ret

  ### REACTION HANDLERS
  ### Using on_raw_reaction_x here instead of on_reaction_x so that the bot
  ### will still process polls after a restart, when the internal cache is
  ### cleared.
  async def on_reaction(self, payload: discord.RawReactionActionEvent, add):
    guild = self.bot.get_guild(payload.guild_id)
    channel = guild.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = guild.get_member(payload.user_id)

    if (user == self.bot.user): return

    cursor = self.conn.cursor()

    # get poll
    poll = sql_request(cursor,
                       "UPDATE Polls SET LastUpdate=%s WHERE "
                       "Message=%s AND Channel=%s RETURNING PollID;",
                       (datetime.now(),
                        self.snowflake_to_str(payload.message_id),
                        self.snowflake_to_str(payload.channel_id)))

    # if a reaction was added to a non-poll, ignore it
    if not poll:
      return
    poll = poll[0]

    # custom emojis are not allowed on polls
    if not payload.emoji.is_unicode_emoji():
      await message.remove_reaction(payload.emoji, user)
      return

    # neither are multi-codepoint emojis (sorry, country flags and skin tones)
    if len(payload.emoji.name) > 1:
      await message.remove_reaction(payload.emoji, user)
      return

    # get codepoint of emoji as string
    emoji = self.emoji_to_str(payload.emoji.name)

    # get option
    option = sql_request(cursor,
                         "SELECT OptionID FROM Options WHERE "
                         "PollID=%s AND Emoji=%s;",
                         (poll, emoji))

    # emoji not a real option--remove it
    if not option:
      await message.remove_reaction(payload.emoji, user)
      return
    option = option[0]

    # remove old vote
    cursor.execute("DELETE FROM Votes WHERE "
                   "Username=%s AND OptionID=%s;",
                   (self.snowflake_to_str(payload.user_id), option))

    # add new vote
    if add:
      cursor.execute("INSERT INTO Votes "
                     "(Username, OptionID) VALUES (%s, %s);",
                     (self.snowflake_to_str(payload.user_id), option))

    await message.edit(content=self.get_poll_string(guild, poll))

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    await self.on_reaction(payload, add=True)

  @commands.Cog.listener()
  async def on_raw_reaction_remove(self,
                                   payload: discord.RawReactionActionEvent):
    await self.on_reaction(payload, add=False)

  @commands.group()
  @delete_source
  async def poll(self, ctx: commands.context):
    if ctx.invoked_subcommand is None:
      await send(ctx, self.messages.errors.command_not_found,
                 tag=True, expire=True)

  @poll.command()
  async def create(self, ctx: commands.context, *args):

    errors = self.messages.errors
    requests = self.messages.sql_requests

    if len(args) == 0:
      await send(ctx, errors.wrong_arg_length,
                 tag=True, expire=True)
      return

    question = args[0]

    if len(question) > MAX_QUESTION_LENGTH:
      await send(ctx, errors.question-too-long,
                 tag=True, expire=True)
      return

    if len(args) > 1:
      if max(len(option) for option in args[1:]) > MAX_OPTION_LENGTH:
        await send(ctx, errors.options_too_long,
                   tag=True, expire=True)
        return

    message = await send(ctx, self.messages.messages.loading,
                         tag=False, expire=False)

    message_flake = self.snowflake_to_str(message.id)
    channel_flake = self.snowflake_to_str(ctx.channel.id)
    user_flake = self.snowflake_to_str(ctx.author.id)

    # catch question-too-long and options_too_long errors

    cursor = self.conn.cursor()

    cursor.execute(requests.new_poll,
                   (question, user_flake, datetime.now(),
                    datetime.now(), message_flake, channel_flake))

    poll_id = cursor.fetchone()[0]

    if len(args) == 1:
      options = zip(self.messages.default_poll.options,
                    self.messages.default_poll.emojis)
    else:
      options = zip(args[1:],
                    self.messages.emojis)

    for option, emoji in options:
      cursor.execute(requests.new_option,
                     (poll_id, True, user_flake, emoji, option))
      await message.add_reaction(self.str_to_emoji(emoji))

    message_string = self.get_poll_string(ctx.guild, poll_id)
    await message.edit(content=message_string)

    header = self.messages.style.poll_header.format(poll_id,
                                                          ctx.author.name)
    q_str = self.messages.style.question_string.format(question)




  @poll.command()
  async def append(self, ctx: commands.context, *args):

    requests = self.messages.sql_requests
    errors = self.messages.errors

    if len(args) < 2:
      await send(ctx, errors.wrong_arg_length, tag=True, expire=True)
      return

    try:
      id = int(args[0], 10)
    except ValueError:
      await send(ctx, errors.id_is_nan, tag=True, expire=True)
      return

    cursor = self.conn.cursor()

    poll_info = sql_request(cursor, requests.get_message_channel,
                            (datetime.now(), id))
    if not poll_info:
      await send(ctx, errors.poll_not_found)

    emojis = sql_request(cursor, requests.get_emojis, (id,))

    if len(emojis) == 0:
      await send(ctx, errors.options_not_found)
      return

    option = " ".join(args[1:])

    for possible_emoji in self.messages.emojis:
      if possible_emoji not in emojis:
        emoji = possible_emoji
        break
    else:
      await send(ctx, errors.too_many_options, tag=True, expire=True)
      return

    cursor.execute(self.messages.sql_requests.new_option,
                   (id, False, self.snowflake_to_str(ctx.author.id),
                    emoji, option))

    channel = ctx.guild.get_channel(self.str_to_snowflake(poll_info.channel))
    if not channel:
      await send(ctx, errors.poll_deleted, tag=True, expire=True)
      return
    try:
      message = await ctx.fetch_message(self.str_to_snowflake(poll_info.message))
    except discord.NotFound:
      await send(ctx, errors.poll_deleted, tag=True, expire=True)
      return

    await message.edit(content=self.get_poll_string(ctx.guild, id))
    await message.add_reaction(self.str_to_emoji(emoji))

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

    cursor.execute(self.messages.sql_requests.reset);
