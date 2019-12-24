from discord.ext import commands
from src.cogs.help import HelpCog
from src.cogs.poll import PollCog
import psycopg2
import os
def main():
  bot = commands.Bot(command_prefix="!")
  bot.remove_command('help')

  bot.add_cog(HelpCog('data/help.yaml', bot))

  conn = psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')
  conn.set_session(readonly=False, autocommit=True)

  bot.add_cog(PollCog('data/poll.yaml', cursor=conn.cursor(), bot=bot))

  bot.run(os.environ['DISCORD_KEY'])



if __name__ == "__main__":
  main()
