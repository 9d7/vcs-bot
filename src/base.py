from discord.ext import commands
from functools import wraps

USER_DELETE_DELAY = 3
BOT_DELETE_DELAY = 10


def delete_source(f):
  @wraps(f)
  async def wrapper(*args, **kwds):
    await args[1].message.delete(delay=USER_DELETE_DELAY)
    return await f(*args, **kwds)

  return wrapper


async def send(ctx: commands.context, message: str, tag: bool, expire: bool):
  if tag:
    message = " ".join([ctx.author.mention, message])

  if expire:
    return await ctx.send(content=message, delete_after=BOT_DELETE_DELAY)
  else:
    return await ctx.send(content=message)
