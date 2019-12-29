import discord
from ruamel.yaml import YAML
from src.base import *


class HelpCog(commands.Cog):

    def _get_base_help_msg(self):
        embed = discord.Embed(
            color=discord.Color.red(),
            title=self.help_text['meta']['title']
        )

        for key in sorted(self.help_text):
            if key == 'meta':
                continue

            brief = self.help_text[key]['brief']

            embed.add_field(
                name=key,
                value=brief,
                inline=True
            )

            embed.set_footer(text=self.help_text['meta']['footer'])

        return embed

    def __init__(self, help_file: str, bot: commands.Bot):

        yaml = YAML(typ='safe')
        with open(help_file, 'r') as help_fd:
            self.help_text = yaml.load(help_fd)

        self.bot = bot
        self.base_help_msg = self._get_base_help_msg()

    @commands.command()
    @delete_source
    async def help(self, ctx: commands.context, *args):
        if len(args) == 0:
            await ctx.send(embed=self.base_help_msg)
            return

        text = self.help_text
        for i, val in enumerate(args):
            if val not in text:
                if i == 0:
                    format_msg = self.help_text['meta']['errors']['no_base_command']
                    await send(ctx, format_msg.format("!" + val), tag=True, expire=True)
                else:
                    format_msg = self.help_text['meta']['errors']['no_subcommand']
                    await send(ctx, format_msg.format(val, "!" + " ".join(args[:i])),
                               tag=True, expire=True)
                return

            text = text[val]

        embed = discord.Embed(
            color=discord.Color.red()
        )

        command_name = "!" + " ".join(args)
        embed.set_author(name=command_name)
        embed.add_field(name=self.help_text['meta']['description_tag'],
                        value=text['description'],
                        inline=False)

        # determine if command is group. we do this by checking for a key
        # that isn't 'brief', 'description', or 'usage'
        filtered_keys = []
        for key in text:
            if key not in ('brief', 'description', 'usage'):
                filtered_keys.append(key)

        if len(filtered_keys) == 0:
            # command

            # determine usage string. usage can be defined as a list or a string,
            # or not defined at all. we handle each of these cases.

            # if usage is not defined, this returns an empty string
            usage = text.get('usage', "")

            # list of usages
            if isinstance(usage, list):

                # join usages with newline
                usage = "\n".join(command_name + " " + i for i in usage)
            else:
                # single usage
                usage = command_name + " " + usage

            # add usage as second field
            embed.add_field(name=self.help_text['meta']['usage_tag'],
                            value=usage,
                            inline=False)
            embed.set_footer(text=self.help_text['meta']['footer'])

        else:
            # add subcommands as fields
            for key in filtered_keys:
                embed.add_field(name=key,
                                value=text[key]['brief'],
                                inline=True)

        await ctx.send(embed=embed)
