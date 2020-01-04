import discord
from discord.ext import commands
from src.base import *
import box
from typing import Optional


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

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

    @commands.group()
    @commands.check(non_dm)
    @delete_source
    async def parrot(self, ctx: commands.context):
        pass

    @parrot.command()
    async def create(self, ctx: commands.context, *args):
        pass
    
    @parrot.command(aliases=['remove'])
    async def delete(self, ctx: commands.context, *args):
        pass
    
    @parrot.command()
    async def view(self, ctx: commands.context, *args):
        pass
    
    @parrot.command()
    async def alias(self, ctx: commands.context, *args):
        pass
    
    @parrot.command()
    async def toggle(self, ctx: commands.context, *args):
        pass
    
    @parrot.group()
    async def response(self, ctx: commands.context):
        pass

    @response.command()
    async def add(self, ctx: commands.context, *args):
        pass

    @response.command(aliases=['remove'])
    async def delete(self, ctx: commands.context, *args):
        pass
