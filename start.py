import os
import sys

import envvar
import utils.twitch_functions as twitch_function
import cogs.utils.settings as settings
import bot
import website

if sys.argv[1] == "bot":
    for extension in bot.extensions:
        bot.client.load_extension(extension)
    bot.client.run(settings.discord_token)
elif sys.argv[1] == "flask":
    website.app.run(host="flokami.ovh", port=8003)
elif sys.argv[1] == "alembic":
    os.system('alembic revision --autogenerate -m ' + sys.argv[2])
    os.system('alembic upgrade head')
elif sys.argv[1] == "twitch_webhook_update":
    pass
