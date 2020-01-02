from discord.ext import commands
from src.cogs.help import HelpCog
from src.cogs.poll import PollCog
from src.cogs.error import ErrorCog
from src.cogs.role import RoleCog
import psycopg2
import os
def main():
  bot = commands.Bot(command_prefix="!")
  bot.remove_command('help')



  conn = psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')
  conn.set_session(readonly=False, autocommit=True)

  bot.add_cog(HelpCog('data/help.yaml', bot=bot))
  bot.add_cog(PollCog('data/poll.yaml', conn=conn, bot=bot))
# uncomment for error handling
  bot.add_cog(RoleCog('data/role.yaml', bot=bot))
  bot.add_cog(ErrorCog('data/error.yaml', bot=bot))

  bot.run(os.environ['DISCORD_KEY'])



if __name__ == "__main__":
  main()
