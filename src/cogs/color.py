import discord
from discord.ext import commands
from src.base import *
import box
from typing import Optional


class ColorError(CommandError):
    def __init__(self, message):
        super().__init__("color")
        self.message = message



class ColorCog(commands.Cog):

    def __init__(self, color_file: str, bot):
        self.bot = bot
        with open(color_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @commands.group()
    @commands.check(non_dm)
    @delete_source
    async def color(self, ctx: commands.context, *args):

        if len(args) != 1:
            raise WrongArgLength("one")

        color_name = args[0]

        if color_name == "list":

            embed = discord.Embed(
                color=random_color(),
                title=self.messages.list.title,
                description=", ".join(self.messages.default_colors)
            )
            embed.set_footer(text=self.messages.list.footer)

            await ctx.send(embed=embed)
            return



        if color_name in self.messages.default_colors:
            color = self.messages.default_colors[color_name]

        else:
            if len(color_name) not in (6, 7):
                raise ColorError("invalid_color")

            if len(color_name) == 7:
                if color_name[0] != "#":
                    raise ColorError("invalid_color")

                color = color_name[1:]
            else:
                color = color_name

        try:
            color_value = int(color, 16)
        except ValueError:
            raise ColorError("invalid_color")

        # remove all existing color roles for the member
        user = ctx.author
        guild = ctx.guild

        for role in user.roles:
            if role.name.startswith(self.messages.color_prefix):
                await user.remove_roles(role)

        # remove all color roles which now have no members
        for role in guild.roles:
            if role.name.startswith(self.messages.color_prefix) and \
                    len(role.members) == 0:
                await role.delete()

        # get role corresponding to existing color
        role_name = self.messages.color_prefix + color

        for role in guild.roles:
            if role.name == role_name:
                break
        else:
            role = await guild.create_role(
                name=role_name,
                color=discord.Color(color_value),
                permissions=discord.Permissions.none(),
                mentionable=False,
                hoist=False)
            await role.edit(position=99)

        await user.add_roles(role)
        await send(ctx, self.messages.success.format(args[0]),
                   tag=True, expire=True)


