from discord.ext import commands
from src.cogs.help import HelpCog
import os
def main():
  bot = commands.Bot(command_prefix="!")
  bot.remove_command('help')

  bot.add_cog(HelpCog('data/help.yaml', bot))

  bot.run(os.environ['DISCORD_KEY'])


if __name__ == "__main__":
  main()
