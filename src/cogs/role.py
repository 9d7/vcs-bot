import discord, os, asyncio
from src.base import *
from datetime import datetime
import box
import arrow


class RoleError(Exception):
    pass

MIN_ROLE_LEN = 3
MAX_ROLE_LEN = 32

class RoleCog(commands.Cog):

    def __init__(self, role_file: str, bot):
        self.bot = bot
        with open(role_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @commands.group()
    async def role(self, ctx: commands.context):
        if ctx.invoked_subcommand is None:
            raise RoleError("command_not_found")

    # some helper commands to interface with discord roles
    def valid_role_name(self, name: str):
        if name == self.messages.admin_role:
            return False
        if name.startswith(self.messages.color_prefix):
            return False
        return True

    def get_roles(self, guild: discord.Guild):
        for role in guild.roles:
            if not self.valid_role_name(role.name):
                continue
            yield role

    def find_role(self, name: str, guild: discord.Guild):
        name = name.lower()
        for role in self.get_roles(guild):
            if role.name.lower() == name:
                return role
        return None

    @role.command()
    async def create(self, ctx: commands.context, *args):

        if len(args) != 1:
            raise WrongArgLength("one")

        name = args[0]

        if len(name) < MIN_ROLE_LEN:
            raise RoleError("role_too_short")

        if len(name) > MAX_ROLE_LEN:
            raise RoleError("role_too_long")

        if self.find_role(name, ctx.guild):
            raise RoleError("role_exists")

        role = await ctx.guild.create_role(
            name=name,
            permissions=discord.Permissions.none(),
            hoist=False,
            mentionable=True
        )
        await role.edit(position=1)

        await send(ctx, self.messages.created.format(name),
                   tag=True, expire=True)

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
