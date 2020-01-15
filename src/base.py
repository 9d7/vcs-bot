"""
A set of functions that get called often from multiple modules.
sql_request - wraps psycopg2's cursor.execute to make it usable with
              namedtuples.
delete_source - a decorator to delete the message that calls a command.
send - small wrapper for ctx.send that keeps deletion and tagging consistent.
random_color - generates a random bright color for embeds.
"""

from discord.ext import commands
import discord
from functools import wraps
import psycopg2
from collections import namedtuple
import random



USER_DELETE_DELAY = 3
BOT_DELETE_DELAY = 10
MAX_TEXT_LENGTH = 2000

RANDOM_COLOR_S = 0.75
RANDOM_COLOR_V = 0.9

CRITICAL_DATABASE_ISSUE = "Critical Error for SQL call:\n{}"


class ArgIsNaN(Exception):
    pass

class WrongArgLength(Exception):
    pass

class PageOOB(Exception):
    pass

class UserNotFound(Exception):
    pass


class Connection(object):
    def __init__(self, conn_func):
        self.conn_func = conn_func
        self.conn = conn_func()

    def cursor(self):
        try:
            return self.conn.cursor()
        except Exception:
            self.conn = self.conn_func()
            return self.conn.cursor()

class CommandError(Exception):
    def __init__(self, command):
     self.command = command

# simple wrapper function to turn psycopg2's returns into named tuples.
# returns a list if single element was requested, otherwise a namedtuple
def sql_request(cursor, call, args):
    """
    Wraps a psycopg2 sql request to make it a bit more human-readable.
    Normally, psycopg2 returns a list of tuples, where the column names
    can be accessed through cursor.description. That is a little unwieldy,
    so this function instead returns a list of namedtuples (from collections)
    where each index in the tuple is annotated with its matching row name.

    :param cursor: the psycopg2 cursor instance to request from.
    :param call: the sql to call.
    :param args: the list of arguments to be passed to the sql request.
    :return: a list of named tuples. if the sql response is one column wide,
    a simple list is returned.
    """
    cursor.execute(call, args)

    desc = [field.name for field in cursor.description]
    Named = namedtuple('sql_return', desc)
    try:
        reply = cursor.fetchall()
    except psycopg2.ProgrammingError:
        print(CRITICAL_DATABASE_ISSUE.format(call))
        return []

    if len(desc) == 1:
        return [i[0] for i in reply]

    return [Named(*i) for i in reply]


def delete_source(f):
    """
    A simple decorator that deletes the invocation message of a command
    after the command is executed.
    :param f: The function to wrap
    :return: The wrapped function
    """
    @wraps(f)
    async def wrapper(*args, **kwds):
        await args[1].message.delete(delay=USER_DELETE_DELAY)
        return await f(*args, **kwds)

    return wrapper


async def send(ctx, message: str, tag: bool, expire: bool):
    """
    A small wrapper for ctx.send that standardizes tagging the invoker in a
    message as well as deleting the message after it was sent.
    :param ctx: The command context
    :param message: The message to send
    :param tag: True to tag the author of the command
    :param expire: True to delete this message after some time
    :return: The sent message.
    """
    if tag:
        message = ctx.author.mention + " " + message

    if expire:
        return await ctx.send(content=message, delete_after=BOT_DELETE_DELAY)
    else:
        return await ctx.send(content=message)


def random_color():
    """
    Creates a random, saturated color.
    :return: A random discord.Color.
    """
    h = random.uniform(0, 1)
    return discord.Color.from_hsv(h, RANDOM_COLOR_S, RANDOM_COLOR_V)


async def send_dm(user: discord.User, message: str):
    """
    A simple wrapper to send a DM to a user, creating the dm channel if it
    does not yet exist.
    :param user: The user to DM
    :param message: The message to send
    :return: The message sent
    """
    if not user.dm_channel:
        await user.create_dm()

    return await user.dm_channel.send(content=message)


async def non_dm(ctx: commands.Context):
    """
    A one-line check to ensure that a command is not invoked through
    DM.
    :param ctx: the context of the command.
    :return: True if we are in a standard text channel.
    """
    return ctx.channel.type == discord.ChannelType.text

def find_user(guild: discord.Guild, name: str):
    """
    A small function to find a user in a guild.
    :param guild: The guild to search
    :param name: The name to search for
    :return: The found user, or None if no user was found.
    """
    name = name.lower()
    for member in guild.members:
        if member.name.lower().startswith(name):
            return member

    for member in guild.members:
        if not member.nick:
            continue
        if member.nick.lower().startswith(name):
            return member

    return None