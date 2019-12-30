# vcs-bot
A small discord bot.

## Hey, what's this?
My group of friends made the leap and switched from Facebook Messenger to Discord recently (mostly for separate channels),
but some of the features present in Messenger were missed in Discord. The main thing was nicknames: in Messenger, chats are
full anarchy, and anybody can set anybody else's nickname. In Discord, however, there's a strong heirarchical structure:
you can only set the nicknames of yourself and the people with server roles below you. This meant that no matter what, the
server owner could never have their nickname set by anybody else.

To fix this, I'm making **vcs-bot**, which is a bot that owns the server it runs on. By having the bot own the server, we
don't have to worry about who has which role, since the bot has total control over nicknames, role management, etc.  

## Oh, cool! So, can I use it?
Well, currently, not really. The bot is set up to only allow me to add new servers for it to run on, and it's really only
meant for use among friends and on small servers. You're welcome to steal the code and build your own bot out of it, though.
Eventually, when the bot is closer to being finished, I'll write a little description of how to install it yourself.

## Dependencies
- [discord.py](https://pypi.org/project/discord.py/)
- [ruamel.yaml](https://pypi.org/project/ruamel.yaml/)
- [python-box](https://pypi.org/project/python-box/)
- [psycopg2](https://pypi.org/project/psycopg2-binary/)
- [arrow](https://pypi.org/project/arrow/)
