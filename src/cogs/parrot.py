import discord, os, asyncio
from discord.ext import commands
from src.base import *
import box
from typing import Optional

MIN_TRIGGER_LEN = 3
MAX_TRIGGER_LEN = 255
MAX_RESPONSE_LEN = 255


class ParrotError(CommandError):
    def __init__(self, message):
        super().__init__("parrot")
        self.message = message


class ParrotCog(commands.Cog):

    def __init__(self, parrot_file: str, conn, bot):
        self.bot = bot
        self.conn = conn
        with open(parrot_file, 'r') as msg_file:
            self.messages = box.Box.from_yaml(msg_file)
        self.toggle = True

    def get_parrot(self, trigger):

        trigger = trigger.lower()

        cursor = self.conn.cursor()
        requests = self.messages.sql_requests

        # search for exact match
        parrot_ids = sql_request(cursor,
                                 requests.get_id,
                                 (trigger,))

        if len(parrot_ids) > 1:
            raise ParrotError("multiple_parrots")
        elif len(parrot_ids) == 1:
            return parrot_ids[0]

        parrot_ids = sql_request(cursor,
                                 requests.get_id,
                                 (trigger + "%",))
        if len(parrot_ids) > 1:
            raise ParrotError("multiple_parrots")
        if len(parrot_ids) == 0:
            raise ParrotError("parrot_not_found")

        return parrot_ids[0]

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.channel.type != discord.ChannelType.text:
            return
        if not self.toggle:
            return
        if message.author == self.bot.user:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        requests = self.messages.sql_requests

        cursor = self.conn.cursor()

        parrot_ids = sql_request(cursor,
                                 requests.search_message,
                                 (message.content.lower(),))

        for parrot_id in parrot_ids:
            response = sql_request(cursor,
                                   requests.random_response,
                                   (parrot_id,))
            if not response:
                continue
            response = response[0]

            await message.channel.send(content=response)

    @commands.group()
    @commands.check(non_dm)
    @delete_source
    async def parrot(self, ctx: commands.context):
        if ctx.invoked_subcommand is None:
            raise ParrotError("command_not_found")

    @parrot.command()
    async def create(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        style = self.messages.style.create

        if len(args) < 2:
            raise WrongArgLength("at least two")

        trigger = args[0].lower()
        responses = args[1:]

        if len(trigger) < MIN_TRIGGER_LEN:
            raise ParrotError("trigger_too_short")
        if len(trigger) > MAX_TRIGGER_LEN:
            raise ParrotError("trigger_too_long")
        for response in responses:
            if len(response) > MAX_RESPONSE_LEN:
                raise ParrotError("responses_too_long")

        cursor = self.conn.cursor()

        # check for existing ID
        parrot_id = sql_request(cursor,
                                requests.get_id,
                                (trigger,))

        if parrot_id:
            raise ParrotError("parrot_exists")

        parrot_id = sql_request(cursor, requests.new_parrot, ())[0]

        cursor.execute(requests.insert_trigger,
                       (parrot_id, trigger, False))

        for response in responses:
            cursor.execute(requests.insert_response,
                           (parrot_id, response))

        await send(ctx, style.success.format(trigger),
                   tag=True, expire=True)

    @parrot.command(aliases=['remove'])
    async def delete(self, ctx: commands.context, *args):

        if len(args) != 1:
            raise WrongArgLength("one")

        cursor = self.conn.cursor()
        requests = self.messages.sql_requests
        style = self.messages.style.delete

        triggers = sql_request(cursor,
                               requests.get_matching_triggers,
                               (args[0],))[0]

        if triggers.nummatches > 1:
            raise ParrotError("multiple_parrots")
        elif triggers.nummatches == 0:
            triggers = sql_request(cursor,
                                   requests.get_matching_triggers,
                                   (args[0] + "%",))[0]
            if triggers.nummatches > 1:
                raise ParrotError("multiple_parrots")
            elif triggers.nummatches == 0:
                raise ParrotError("parrot_not_found")

        if triggers.alias:
            cursor.execute(requests.delete_alias,
                           (triggers.trigger, triggers.parrotid))
            await send(
                ctx,
                style.success_alias.format(triggers.trigger),
                tag=True, expire=True)
        else:
            cursor.execute(requests.delete_parrot,
                           (triggers.parrotid,) * 3)
            await send(
                ctx,
                style.success.format(triggers.trigger),
                tag=True, expire=True)

    @parrot.command()
    async def view(self, ctx: commands.context, *args):

        if len(args) != 1:
            raise WrongArgLength("one")

        requests = self.messages.sql_requests
        style = self.messages.style.view

        parrot_id = self.get_parrot(args[0])

        cursor = self.conn.cursor()
        view_params = sql_request(cursor, requests.get_view, (parrot_id,) * 3)

        if len(view_params) == 0:
            raise ParrotError("parrot_not_found")
        elif len(view_params) > 1:
            raise ParrotError("multiple_parrots")

        view_params = view_params[0]

        embed = discord.Embed(
            color=random_color(),
            title=style.title.format(view_params.trigger)
        )

        if view_params.aliases:
            embed.add_field(name=style.alias_title,
                            value=view_params.aliases,
                            inline=False)

        embed.add_field(name=style.responses_title,
                        value=view_params.responses,
                        inline=False)

        await ctx.send(embed=embed)




    @parrot.command()
    async def alias(self, ctx: commands.context, *args):

        requests = self.messages.sql_requests
        style = self.messages.style.alias

        if len(args) != 2:
            raise WrongArgLength("two")

        parrot_id = self.get_parrot(args[0])

        alias = args[1].lower()
        if len(alias) < MIN_TRIGGER_LEN:
            raise ParrotError("alias_too_short")
        if len(alias) > MAX_TRIGGER_LEN:
            raise ParrotError("alias_too_long")

        cursor = self.conn.cursor()

        # check that there are no other exact matches for that alias,
        # since multiple exact aliases leads to ambiguity
        matching_triggers = sql_request(cursor,
                                        requests.get_matching_triggers,
                                        (alias,))[0]
        if matching_triggers.nummatches > 0:
            raise ParrotError("alias_exists")

        cursor.execute(requests.insert_trigger, (parrot_id, alias, True))
        await send(ctx,
                   style.success.format(alias),
                   tag=True, expire=True)

    @parrot.command()
    async def toggle(self, ctx: commands.context, *args):
        self.toggle = not self.toggle
        style = self.messages.style.toggle
        if self.toggle:
            await send(ctx,
                       style.enable,
                       tag=True, expire=True)
        else:
            await send(ctx,
                       style.disable,
                       tag=True, expire=True)

    @parrot.group()
    async def response(self, ctx: commands.context):
        if ctx.invoked_subcommand is None:
            raise ParrotError("command_not_found")

    @response.command(name='add', aliases=['create'])
    async def response_add(self, ctx: commands.context, *args):

        if len(args) != 2:
            raise WrongArgLength("two")

        if len(args[1]) > MAX_RESPONSE_LEN:
            raise ParrotError("response_too_long")

        requests = self.messages.sql_requests
        style = self.messages.style.response_add

        parrot_id = self.get_parrot(args[0])

        cursor = self.conn.cursor()

        cursor.execute(requests.insert_response,
                       (parrot_id, args[1]))

        await send(ctx,
                   style.success.format(args[1]),
                   tag=True, expire=True)



    @response.command(name='delete', aliases=['remove'])
    async def response_remove(self, ctx: commands.context, *args):
        pass

    @parrot.command()
    async def reset(self, ctx: commands.context, *args):
        style = self.messages.style.password

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
