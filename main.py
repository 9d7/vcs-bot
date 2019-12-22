from discord.ext import commands
from cogs.help import HelpCog

def main():
  bot = commands.Bot(command_prefix="!")
  bot.remove_command('help')

  bot.add_cog(HelpCog('help.yaml', bot))



if __name__ == "__main__":
  main()
