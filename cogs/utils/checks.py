from discord.ext import commands
import cogs.utils.models as models


def is_owner_check(message):
    return str(message.author.id) == "188508216995348483"


def is_owner():
    return commands.check(lambda ctx: is_owner_check(ctx.message))


def is_private_check(message):
    if(message.channel != message.author.dm_channel):
        message.content = "is_private"
    return message.channel == message.author.dm_channel


def is_private():
    return commands.check(lambda ctx: is_private_check(ctx.message))


def is_server_check(message):
    if(message.channel == message.author.dm_channel):
        message.content = "is_server"
    return message.channel != message.author.dm_channel


def is_server():
    return commands.check(lambda ctx: is_server_check(ctx.message))


def is_server_admin_check(message):
    if is_server_check(message):
        server = models.session.query(
            models.Server).filter(models.Server.server_id ==
                                  str(message.guild.id)).first()
        return server.admin_id == str(message.author.id)
    else:
        message.content = "is_server"
        return False


def is_server_admin():
    return commands.check(lambda ctx: is_server_admin_check(ctx.message))
