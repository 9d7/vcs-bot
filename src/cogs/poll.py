from discord.ext import commands
import discord
import psycopg2
import box
from ruamel.yaml import YAML
import datetime


class PollCog(commands.Cog):

  class Option(object):
    def __init__(self, option_id: int, original: bool,
                 username: str, emoji: str, option: str):
      self.option_id = option_id
      self.original = original
      self.username = username
      self.emoji = emoji
      self.option = option
      self.votes = []

    def add_vote(self, cursor, username):
      if username not in self.votes:
        self.votes.append(username)
        cursor.execute("INSERT INTO Votes (Username, OptionID) "
                       "VALUES (%s, %s);",
                       (username, self.option_id))

    def del_vote(self, cursor, username):
      self.votes[:] = [v for v in self.votes if v != username]
      cursor.execute("DELETE FROM Votes WHERE Username=%s AND OptionID=%s;",
                     (username, self.option_id))
    # whether the option is purgable--i.e., whether it hasn't received
    # any votes. if force, then the option is also purgable if the only
    # vote was given by its creator. original options are never purgable.
    def is_purgable(self, force):

      # original - don't purge
      if self.original:
        return False

      # no votes - always purge
      if len(self.votes) == 0:
        return True

      # multiple votes - don't purge
      if len(self.votes) > 1:
        return False

      # non-creator voted - don't purge
      if self.votes[0] != self.username:
        return False

      # creator voted - purge if force
      return force



  class Poll(object):

    def __init__(self, poll_id: int, question: str,
                 username: str, time: datetime.datetime,
                 last_update: datetime.datetime, message: str,
                 channel: str):
      self.poll_id = poll_id
      self.question = question
      self.username = username
      self.time = time
      self.last_update = last_update
      self.message = message
      self.channel = channel
      self.options = []


    @staticmethod
    def new_poll(cursor, question: str, username: str, message: str,
                 channel: str):
      time = datetime.datetime.now()
      last_update = datetime.datetime.now()

      cursor.execute("INSERT INTO Polls "
                     "(Question, Username, Time, LastUpdate, Message, Channel) "
                     "VALUES (%s, %s, %s, %s, %s, %s) RETURNING PollID;",
                     (question, username, time, last_update, message, channel))
      poll_id = cursor.fetchone()[0]

      return PollCog.Poll(poll_id, question, username, time, last_update,
                          message, channel)

    def add_option(self, cursor, original: bool, username: str,
                   emoji: str, option: str):
      cursor.execute("INSERT INTO Options "
                     "(PollID, Original, Username, Emoji, Option) "
                     "VALUES (%s, %s, %s, %s, %s) RETURNING OptionID;",
                     (self.poll_id, original, username, emoji, option))
      option_id = cursor.fetchone()[0]
      self.options.append(PollCog.Option(option_id, original, username,
                                         emoji, option))

    def remove_option(self, cursor, option_id):
      if option_id in [i.option_id for i in self.options]:
        self.options[:] = [i for i in self.options if i.option_id != option_id]
        cursor.execute("DELETE FROM Options WHERE OptionID=%s;",
                       (option_id, self.poll_id))
        cursor.execute("DELETE FROM Votes WHERE OptionID=%s;", (option_id))

    def purge(self, cursor, force):
      to_remove = [i.option_id for i in self.options if i.is_purgable(force)]
      for option in to_remove:
        self.remove_option(cursor, option)

  def __init__(self, poll_file: str, cursor, bot: commands.Bot):
    self.bot = bot
    self.cursor = cursor
    with open(poll_file, 'r') as error:
      self.error_text = YAML(typ='safe').load(error)

    


