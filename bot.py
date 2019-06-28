import threading
from datetime import datetime
import sys

import discord
from discord.ext.commands import Bot
from discord.ext.commands.errors import CheckFailure

import website
import cogs.utils.settings as settings
import cogs.utils.models as models
import cogs.utils.languages as lang

client = Bot(command_prefix=settings.BOT_PREFIX)

extensions = [
    "cogs.admin",
    "cogs.twitter",
    "cogs.twitch"
]


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.guilds)
    print(client.user.id)
    print('------')
    game = discord.Game(name="Connected on " + str(len(client.guilds))
                        + " servers ", start=datetime.now())
    await client.change_presence(activity=game)
    for guild in client.guilds:
        server = models.session.query(
            models.Server).filter(models.Server.server_id ==
                                  str(guild.id)).first()
        if server is None:
            serv = models.Server(
                server_id=str(guild.id),
                server_name=guild.name,
                discord_admin_id=str(guild.owner.id),
                admin_name=guild.owner.name
            )
            models.session.add(serv)
            models.session.flush()
            admin = models.session.query(models.User).filter(
                models.User.discord_user_id == serv.discord_admin_id
            ).first()
            if admin is not None:
                serv.admin_id = admin.id
                models.session.flush()
            models.session.commit()


@client.event
async def on_guild_join(guild):
    game = discord.Game(name="Connected on " + str(len(client.guilds))
                        + " servers ", start=datetime.now())
    await client.change_presence(activity=game)
    serv = models.Server(
        server_id=str(guild.id),
        server_name=guild.name,
        discord_admin_id=str(guild.owner.id),
        admin_name=guild.owner.name
    )
    models.session.add(serv)
    models.session.commit()


@client.event
async def on_raw_reaction_add(payload):
    print(payload.message_id)


@client.event
async def on_command_error(ctx, error):
    if type(error) == CheckFailure:
        user = models.session.query(models.User).filter(
            models.User.discord_user_id == str(ctx.author.id)
        ).first()
        lang.set_actual_lang_for_user(user, "FR")
        if(ctx.message.content == "is_private"):
            await ctx.send('\N{NO ENTRY} ' +
                           lang.return_string(user, 'is_private_error')
                           + ' \N{NO ENTRY} ')
            await ctx.message.author.send(
                lang.lang.return_string(user, 'is_private_error', 1))
        if(ctx.message.content == "is_server"):
            await ctx.send('\N{NO ENTRY} ' +
                           lang.return_string(user, 'is_server_error')
                           + ' \N{NO ENTRY} ')
    else:
        print(error)


if __name__ == '__main__':
    for extension in extensions:
        client.load_extension(extension)
    flasktr = threading.Thread(target=website.app.run)
    bottr = threading.Thread(target=client.run, args=(
        settings.discord_bot_token,))
    bottr.start()
