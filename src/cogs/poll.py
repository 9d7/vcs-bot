import discord, os, asyncio
from src.base import *
from datetime import datetime
import box
import arrow

MAX_QUESTION_LENGTH = 255
MAX_OPTION_LENGTH = 80
POLLS_PER_PAGE = 10


class PollCog(commands.Cog, command_attrs=dict(no_pm=True)):

    def __init__(self, poll_file: str,
                 conn, bot: commands.Bot):
        self.bot = bot
        self.conn = conn
        with open(poll_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)

    @staticmethod
    def emoji_to_str(flake: str):
        return "{0:08X}".format(ord(flake))

    @staticmethod
    def str_to_emoji(emoji: str):
        return chr(int(emoji, base=16))

    @staticmethod
    def snowflake_to_str(flake: int):
        return "{0:016X}".format(flake)

    @staticmethod
    def snowflake_to_user(guild: discord.Guild, flake: str):
        return guild.get_member(user_id=int(flake, 16)).display_name

    @staticmethod
    def str_to_snowflake(flake: str):
        return int(flake, 16)


    def get_option_string(self, guild: discord.Guild, poll_id: int):

        requests = self.messages.sql_requests
        style = self.messages.style

        cursor = self.conn.cursor()

        # get option info, ordered from most to fewest votes
        options = sql_request(cursor,
                              requests.readout, (poll_id,))

        option_strings = []

        # get option readout
        for option in options:

            emoji = self.str_to_emoji(option.emoji)

            # get votes
            if option.votes:
                users = option.votes.split(" ")
                users = [self.snowflake_to_user(guild, user) for user in users]
                all_votes = ", ".join(users)
            else:
                all_votes = style.no_votes

            # format options string

            vote_str = style.vote_plural
            if option.votecount == 1:
                vote_str = style.vote_singular

            final_string = style.option_string.format(
                option.votecount, vote_str, emoji, option.option, all_votes)

            option_strings.append(final_string)

        return "\n".join(option_strings)

    def get_poll_string(self, guild: discord.Guild, poll_id):

        style = self.messages.style
        errors = self.messages.errors
        requests = self.messages.sql_requests

        cursor = self.conn.cursor()

        # get poll info
        poll_info = sql_request(cursor,
                                requests.get_poll,
                                (poll_id,))[0]

        username = self.snowflake_to_user(guild, poll_info.username)

        # format strings
        header_string = style.poll_header.format(poll_id,
                                                 username)
        question_string = style.question_string.format(poll_info.question)

        option_string = self.get_option_string(guild, poll_id)

        # join string together :)
        ret = "\n".join([header_string, question_string, option_string])
        if len(ret) >= MAX_TEXT_LENGTH:
            return errors.poll_overflow

        return ret

    # REACTION HANDLERS
    # Using on_raw_reaction_x here instead of on_reaction_x so that the bot
    # will still process polls after a restart, when the internal cache is
    # cleared.
    async def on_reaction(self, payload: discord.RawReactionActionEvent, add):

        requests = self.messages.sql_requests

        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = guild.get_member(payload.user_id)

        if user == self.bot.user:
            return

        cursor = self.conn.cursor()

        # get poll
        poll = sql_request(cursor,
                           requests.get_id_from_message,
                           (datetime.utcnow(),
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

        # neither are multi-codepoint emojis (sorry, country flags)
        if len(payload.emoji.name) > 1:
            await message.remove_reaction(payload.emoji, user)
            return

        # get codepoint of emoji as string
        emoji = self.emoji_to_str(payload.emoji.name)

        # get option
        option = sql_request(cursor, requests.option_from_emoji,
                             (poll, emoji))

        # emoji not a real option--remove it
        if not option:
            await message.remove_reaction(payload.emoji, user)
            return
        option = option[0]

        # remove old vote
        cursor.execute(requests.remove_vote,
                       (self.snowflake_to_str(payload.user_id), option))

        # add new vote
        if add:
            cursor.execute(requests.add_vote,
                           (self.snowflake_to_str(payload.user_id), option))

        await message.edit(content=self.get_poll_string(guild, poll))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,
                                  payload: discord.RawReactionActionEvent):
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

    ############################################################################
    # create
    ############################################################################

    @poll.command()
    @commands.check(non_dm)
    async def create(self, ctx: commands.context, *args):

        errors = self.messages.errors
        requests = self.messages.sql_requests

        if len(args) == 0:
            await send(ctx, errors.wrong_arg_length,
                       tag=True, expire=True)
            return

        question = args[0]

        if len(question) > MAX_QUESTION_LENGTH:
            await send(ctx, errors.question_too_long,
                       tag=True, expire=True)
            return

        if len(args) > 1:
            if max(len(option) for option in args[1:]) > MAX_OPTION_LENGTH:
                await send(ctx, errors.options_too_long,
                           tag=True, expire=True)
                return

        message = await send(ctx, self.messages.style.loading,
                             tag=False, expire=False)

        message_flake = self.snowflake_to_str(message.id)
        channel_flake = self.snowflake_to_str(ctx.channel.id)
        user_flake = self.snowflake_to_str(ctx.author.id)

        # catch question-too-long and options_too_long errors

        cursor = self.conn.cursor()

        cursor.execute(requests.new_poll,
                       (question, user_flake, datetime.utcnow(),
                        datetime.utcnow(), message_flake, channel_flake))

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

    ############################################################################
    # append
    ############################################################################

    @poll.command()
    @commands.check(non_dm)
    async def append(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        errors = self.messages.errors

        if len(args) < 2:
            await send(ctx, errors.wrong_arg_length, tag=True, expire=True)
            return

        try:
            poll_id = int(args[0], 10)
        except ValueError:
            await send(ctx, errors.id_is_nan, tag=True, expire=True)
            return

        cursor = self.conn.cursor()

        poll_info = sql_request(cursor, requests.get_message_from_id,
                                (datetime.utcnow(), poll_id))
        if not poll_info:
            await send(ctx, errors.poll_not_found, tag=True, expire=True)

        poll_info = poll_info[0]

        emojis = sql_request(cursor, requests.get_emojis, (poll_id,))

        if len(emojis) == 0:
            await send(ctx, errors.options_not_found, tag=True, expire=True)
            return

        option = " ".join(args[1:])

        if len(option) > MAX_OPTION_LENGTH:
            await send(ctx, errors.option_too_long, tag=True, expire=True)

        for possible_emoji in self.messages.emojis:
            if possible_emoji not in emojis:
                emoji = possible_emoji
                break
        else:
            await send(ctx, errors.too_many_options, tag=True, expire=True)
            return

        cursor.execute(self.messages.sql_requests.new_option,
                       (poll_id, False, self.snowflake_to_str(ctx.author.id),
                        emoji, option))

        channel = ctx.guild.get_channel(
            self.str_to_snowflake(poll_info.channel)
        )
        if not channel:
            await send(ctx, errors.poll_deleted, tag=True, expire=True)
            return
        try:
            message = await ctx.fetch_message(
                self.str_to_snowflake(poll_info.message))
        except discord.NotFound:
            await send(ctx, errors.poll_deleted, tag=True, expire=True)
            return

        await message.edit(content=self.get_poll_string(ctx.guild, poll_id))
        await message.add_reaction(self.str_to_emoji(emoji))

    ############################################################################
    # list
    ############################################################################

    @poll.command()
    async def list(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        errors = self.messages.errors
        style = self.messages.style

        if len(args) > 1:
            await send(ctx, errors.wrong_arg_length, tag=True, expire=True)
            return

        if len(args) == 0:
            page = 1
        else:
            try:
                page = int(args[0], base=10)
            except ValueError:
                await send(ctx, errors.page_is_nan, tag=True, expire=True)
                return

        if page < 1:
            await send(ctx, errors.page_oob, tag=True, expire=True)
            return

        cursor = self.conn.cursor()

        num_pages = sql_request(
            cursor, requests.num_pages, (POLLS_PER_PAGE,)
        )[0]

        if num_pages == 0:
            await send(ctx, errors.no_polls_to_list, tag=True, expire=True)
            return

        if page > num_pages:
            await send(ctx, errors.page_oob, tag=True, expire=True)
            return

        poll_summaries = sql_request(cursor,
                                     requests.summary,
                                     (style.no_votes_summary,
                                      (page - 1) * POLLS_PER_PAGE,
                                      POLLS_PER_PAGE))

        format_string = style.summary_string
        summaries = "\n".join(
            format_string.format(str(i.pollid).zfill(3), i.question, i.result)
            for i in poll_summaries
        )

        embed = discord.Embed(
            color=random_color(),
            title=style.summary_title,
            description=summaries
        )

        footer = style.summary_footer.format(page, int(num_pages))

        embed.set_footer(text=footer)

        await ctx.send(embed=embed)

    ############################################################################
    # remove
    ############################################################################
    @poll.command()
    @commands.check(non_dm)
    async def delete(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        errors = self.messages.errors

        if len(args) != 1:
            await send(ctx, errors.wrong_arg_length, tag=True, expire=True)
            return

        try:
            poll_id = int(args[0], 10)
        except ValueError:
            await send(ctx, errors.id_is_nan, tag=True, expire=True)
            return

        cursor = self.conn.cursor()

        poll_info = sql_request(cursor, requests.delete_poll_info,
                                (poll_id,))

        if not poll_info:
            await send(ctx, errors.poll_not_found, tag=True, expire=True)
            return
        poll_info = poll_info[0]

        if self.snowflake_to_str(ctx.author.id) != poll_info.username:
            await send(ctx, errors.not_author, tag=True, expire=True)

        # delete old poll if it exists
        channel = ctx.guild.get_channel(
            self.str_to_snowflake(poll_info.channel)
        )
        if channel:
            try:
                message = await channel.fetch_message(
                    self.str_to_snowflake(poll_info.message)
                )
                await message.delete()
            except discord.NotFound:
                pass

        cursor.execute(requests.delete_poll,
                       (poll_id, poll_id, poll_id))

    ############################################################################
    # revive
    ############################################################################

    @poll.command()
    @commands.check(non_dm)
    async def revive(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        errors = self.messages.errors

        if len(args) != 1:
            await send(ctx, errors.wrong_arg_length, tag=True, expire=True)
            return

        try:
            poll_id = int(args[0], 10)
        except ValueError:
            await send(ctx, errors.id_is_nan, tag=True, expire=True)
            return

        cursor = self.conn.cursor()

        poll_info = sql_request(cursor, requests.get_message_from_id,
                                (datetime.utcnow(), poll_id))

        if not poll_info:
            await send(ctx, errors.poll_not_found, tag=True, expire=True)
            return
        poll_info = poll_info[0]

        # delete old poll if it exists
        channel = ctx.guild.get_channel(
            self.str_to_snowflake(poll_info.channel)
        )
        if channel:
            try:
                message = await channel.fetch_message(
                    self.str_to_snowflake(poll_info.message)
                )
                await message.delete()
            except discord.NotFound:
                pass

        # new message
        message = await send(ctx, self.messages.style.loading,
                             tag=False, expire=False)

        cursor.execute(requests.move_poll,
                       (self.snowflake_to_str(message.id),
                        self.snowflake_to_str(ctx.channel.id),
                        poll_id))

        emojis = sql_request(cursor,
                             requests.get_emojis,
                             (poll_id,))
        for emoji in emojis:
            await message.add_reaction(self.str_to_emoji(emoji))

        await message.edit(content=self.get_poll_string(ctx.guild, poll_id))

    ############################################################################
    # view
    ############################################################################

    @poll.command()
    async def view(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        errors = self.messages.errors
        style = self.messages.style

        if len(args) != 1:
            await send(ctx, errors.wrong_arg_length, tag=True, expire=True)
            return

        try:
            poll_id = int(args[0], 10)
        except ValueError:
            await send(ctx, errors.id_is_nan, tag=True, expire=True)
            return

        cursor = self.conn.cursor()

        metadata = sql_request(cursor, requests.poll_metadata, (poll_id,))

        if not metadata:
            await send(ctx, errors.poll_not_found, tag=True, expire=True)
            return
        metadata = metadata[0]

        channel = ctx.guild.get_channel(
            self.str_to_snowflake(metadata.channel)
        )

        if not channel:
            link = None
        else:
            try:
                message = await channel.fetch_message(
                    self.str_to_snowflake(metadata.message)
                )
                link = message.jump_url
            except discord.NotFound:
                link = None

        title = style.overview_title.format(
            poll_id,
            self.snowflake_to_user(ctx.guild, metadata.username))

        if link:
            embed = discord.Embed(
                title=title,
                color=random_color(),
                description=style.overview_link.format(link)
            )
        else:
            embed = discord.Embed(
                title=title,
                color=random_color()
            )

        footer = style.timestamp.format(
            arrow.get(metadata.time).humanize(),
            arrow.get(metadata.lastupdate).humanize()
        )

        embed.set_footer(text=footer)

        embed.add_field(
            name=style.question_title,
            value=metadata.question,
            inline=False
        )

        embed.add_field(
            name=style.option_title,
            value=self.get_option_string(ctx.guild, poll_id),
            inline=False
        )

        await ctx.send(embed=embed)

    ############################################################################
    # purge
    ############################################################################

    @poll.command()
    @commands.check(non_dm)
    async def purge(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        errors = self.messages.errors

        if len(args) not in [1, 2]:
            await send(ctx, errors.wrong_arg_length, tag=True, expire=True)
            return

        try:
            poll_id = int(args[0], 10)
        except ValueError:
            await send(ctx, errors.id_is_nan, tag=True, expire=True)
            return

        cursor = self.conn.cursor()

        force = len(args) > 1

        poll_info = sql_request(cursor,
                                requests.get_message_from_id,
                                (datetime.utcnow(), poll_id))
        if not poll_info:
            await send(ctx, errors.poll_not_found, tag=True, expire=True)
            return
        poll_info = poll_info[0]

        # get old poll message if it exists
        message = None

        channel = ctx.guild.get_channel(
            self.str_to_snowflake(poll_info.channel)
        )
        if channel:
            try:
                message = await channel.fetch_message(
                    self.str_to_snowflake(poll_info.message)
                )
            except discord.NotFound:
                pass

        if force:
            emojis = sql_request(cursor,
                                 requests.purge_force,
                                 (poll_id, poll_id))
        else:
            emojis = sql_request(cursor,
                                 requests.purge,
                                 (poll_id, poll_id))

        # remove options from message
        if message:
            for reaction in message.reactions:

                remove = False
                # custom emojis are not allowed on polls
                if type(reaction.emoji) != str:
                    remove = True

                # neither are multi-codepoint emojis (sorry, country flags)
                if len(reaction.emoji) > 1:
                    remove = True

                elif self.emoji_to_str(reaction.emoji) in emojis:
                    remove = True

                if remove:
                    async for user in reaction.users():
                        await reaction.remove(user)

            await message.edit(
                content=self.get_poll_string(ctx.guild, poll_id)

            )

    @poll.command()
    async def reset(self, ctx: commands.context, *args):

        style = self.messages.style

        await send_dm(ctx.author, style.password_enter)
        channel = ctx.author.dm_channel

        try:
            await self.bot.wait_for(
                'message', timeout=20.0,
                check=lambda x: x.channel == channel and
                                x.author == ctx.author and
                                x.content == os.environ['RESET_PASSWORD'])
        except asyncio.TimeoutError:
            await send_dm(ctx.author, style.password_fail)
        else:
            cursor = self.conn.cursor()
            cursor.execute(self.messages.sql_requests.reset)
            await send_dm(ctx.author, style.password_succeed)



