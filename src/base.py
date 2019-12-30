from discord.ext import commands
import discord
from functools import wraps
import psycopg2
from collections import namedtuple
import random

"""
A set of functions that get called often from multiple modules.
sql_request - wraps psycopg2's cursor.execute to make it usable with
              namedtuples.
delete_source - a decorator to delete the message that calls a command.
send - small wrapper for ctx.send that keeps deletion and tagging consistent.
random_color - generates a random bright color for embeds.
"""

USER_DELETE_DELAY = 3
BOT_DELETE_DELAY = 10
MAX_TEXT_LENGTH = 2000

RANDOM_COLOR_S = 0.75
RANDOM_COLOR_V = 0.9

CRITICAL_DATABASE_ISSUE = "Critical Error for SQL call:\n{}"


# simple wrapper function to turn psycopg2's returns into named tuples.
# returns a list if single element was requested, otherwise a namedtuple
def sql_request(cursor, call, args):
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


# a
def delete_source(f):
    @wraps(f)
    async def wrapper(*args, **kwds):
        await args[1].message.delete(delay=USER_DELETE_DELAY)
        return await f(*args, **kwds)

    return wrapper


async def send(ctx, message: str, tag: bool, expire: bool):
    if tag:
        message = ctx.author.mention + " " + message

    if expire:
        return await ctx.send(content=message, delete_after=BOT_DELETE_DELAY)
    else:
        return await ctx.send(content=message)


def random_color():
    h = random.uniform(0, 1)
    print(h)
    return discord.Color.from_hsv(h, RANDOM_COLOR_S, RANDOM_COLOR_V)


async def send_dm(user: discord.User, message: str):
    if not user.dm_channel:
        await user.create_dm()

    return await user.dm_channel.send(content=message)


async def non_dm(ctx: commands.Context):
    return ctx.channel.type == discord.ChannelType.text
