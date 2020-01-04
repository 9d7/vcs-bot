import discord
from discord.ext import commands
from src.base import *
import box


class RoleError(Exception):
    pass


MIN_ROLE_LEN = 3
MAX_ROLE_LEN = 32


class RoleCog(commands.Cog):

    def __init__(self, role_file: str, bot):
        self.bot = bot
        with open(role_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @commands.group(aliases=['roles'])
    @commands.check(non_dm)
    @delete_source
    async def role(self, ctx: commands.context):
        if ctx.invoked_subcommand is None:
            raise RoleError("command_not_found")

    # some helper commands to interface with discord roles
    def valid_role_name(self, name: str):
        name = name.lower()

        if name in self.messages.reserved_roles:
            return False
        for prefix in self.messages.reserved_prefixes:
            if name.startswith(prefix):
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

        if not self.valid_role_name(name):
            raise RoleError("role_reserved")

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
        if len(args) not in (1, 2):
            raise WrongArgLength("one or two")

        if len(args) == 1:
            user = ctx.author
            role = self.find_role(args[0], ctx.guild)

            if not role:
                raise RoleError("role_not_found")

            if role in user.roles:
                raise RoleError("author_in_role")

            await user.add_roles(role)
            await send(ctx,
                       self.messages.join.author_success.format(role.name),
                       tag=True, expire=True)

            return

        else:
            user = find_user(ctx.guild, args[0])

            if not user:
                raise UserNotFound(args[0])

            role = self.find_role(args[1], ctx.guild)

            if not role:
                raise RoleError("role_not_found")

            if role in user.roles:
                raise RoleError("user_in_role")

            await user.add_roles(role)
            await send(ctx,
                       self.messages.join.success.format(user.mention,
                                                         role.name,
                                                         ctx.author.mention),
                       tag=False, expire=False)

    @role.command()
    async def leave(self, ctx: commands.context, *args):

        if len(args) not in (1, 2):
            raise WrongArgLength("one or two")

        if len(args) == 1:
            user = ctx.author
            role = self.find_role(args[0], ctx.guild)

            if not role:
                raise RoleError("role_not_found")

            if role not in user.roles:
                raise RoleError("author_not_in_role")

            await user.remove_roles(role)
            await send(ctx,
                       self.messages.leave.author_success.format(role.name),
                       tag=True, expire=True)

        else:
            user = find_user(ctx.guild, args[0])

            if not user:
                raise UserNotFound(args[0])

            role = self.find_role(args[1], ctx.guild)

            if not role:
                raise RoleError("role_not_found")

            if role not in user.roles:
                raise RoleError("user_not_in_role")

            await user.remove_roles(role)
            await send(ctx,
                       self.messages.leave.success.format(user.mention,
                                                          role.name,
                                                          ctx.author.mention),
                       tag=False, expire=False)

    @role.command()
    async def list(self, ctx: commands.context, *args):
        all_roles = []
        for role in self.get_roles(ctx.guild):
            members = [member.display_name for member in role.members]
            string = self.messages.list.format_string
            string = string.format(role.name, ", ".join(members))
            all_roles.append(string)


        if len(all_roles) == 0:
            raise RoleError("no_roles")

        embed = discord.Embed(
            color=random_color(),
            title=self.messages.list.title,
            description="\n".join(all_roles)
        )

        await ctx.send(embed=embed)

    @role.command()
    async def delete(self, ctx: commands.context, *args):
        if len(args) != 1:
            raise WrongArgLength("one")

        name = args[0]
        if len(name) < MIN_ROLE_LEN:
            raise RoleError("role_too_short")

        role = self.find_role(name, ctx.guild)
        if not role:
            raise RoleError("role_not_found")

        await role.delete()
        await send(ctx, self.messages.delete.success.format(name),
                   tag=True, expire=True)
