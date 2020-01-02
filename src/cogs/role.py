import discord, os, asyncio
from src.base import *
from datetime import datetime
import box
import arrow


class RoleError(Exception):
    pass


class RoleCog(commands.Cog):

    def __init__(self, role_file: str, bot):
        self.bot = bot
        with open(role_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @commands.group()
    async def role(self, ctx: commands.context):
        if ctx.invoked_subcommand is None:
            raise RoleError("command_not_found")

    @role.command()
    async def create(self, ctx: commands.context, *args):
        pass

    @role.command()
    async def join(self, ctx: commands.context, *args):
        pass

    @role.command()
    async def leave(self, ctx: commands.context, *args):
        pass

    @role.command()
    async def list(self, ctx: commands.context, *args):
        pass

    @role.command()
    async def remove(self, ctx: commands.context, *args):
        pass
