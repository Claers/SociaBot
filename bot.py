import cogs.utils.settings as settings
import cogs.utils.models as models
import cogs.utils.languages as lang
import discord
import asyncio
from datetime import datetime
import sys
from discord.ext.commands import Bot
from discord.ext.commands.errors import CheckFailure

client = Bot(command_prefix=settings.BOT_PREFIX)

extensions = [
    "cogs.admin",
    "cogs.config",
    "cogs.twitter",
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
                admin_id=str(guild.owner.id),
                admin_name=guild.owner.name
            )
            models.session.add(serv)
            models.session.commit()


@client.event
async def on_guild_join(guild):
    serv = models.Server(server_id=str(guild.id), server_name=guild.name,
                         admin_id=str(guild.owner.id),
                         admin_name=guild.owner.name)
    models.session.add(serv)
    models.session.commit()


async def on_command_error(ctx, error):
    if type(error) == CheckFailure:
        if(ctx.message.content == "is_private"):
            await ctx.send('\N{NO ENTRY} ' +
                           lang.ACTUAL['is_private_error'][0]
                           + ' \N{NO ENTRY} ')
            await ctx.message.author.send(
                lang.ACTUAL['is_private_error'][1])
        if(ctx.message.content == "is_server"):
            await ctx.send('\N{NO ENTRY} ' +
                           lang.ACTUAL['is_server_error']
                           + ' \N{NO ENTRY} ')
    else:
        print(error)


if __name__ == '__main__':
    for extension in extensions:
        client.load_extension(extension)
    client.run(settings.DiscordToken)
