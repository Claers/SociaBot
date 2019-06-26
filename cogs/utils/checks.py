from discord.ext import commands
import cogs.utils.models as models


def is_owner_check(message):
    """This check if message is from bot owner id (you have to set it manually,
    it's actually my id here)
    """
    return str(message.author.id) == "188508216995348483"


def is_owner():
    """Decorator function handler
    """
    return commands.check(lambda ctx: is_owner_check(ctx.message))


def is_private_check(message):
    """Check if the message is send in a private channel (direct message)
    """
    if(message.channel != message.author.dm_channel):
        message.content = "is_private"
    return message.channel == message.author.dm_channel


def is_private():
    """Decorator function handler
    """
    return commands.check(lambda ctx: is_private_check(ctx.message))


def is_server_check(message):
    """Check if the message is send in a server channel
    """
    if(message.channel == message.author.dm_channel):
        message.content = "is_server"
    return message.channel != message.author.dm_channel


def is_server():
    """Decorator function handler
    """
    return commands.check(lambda ctx: is_server_check(ctx.message))


def is_server_admin_check(message):
    """Check is message is send by the server admin
    """
    if is_server_check(message):
        return message.guild.owner_id == message.author.id
    else:
        message.content = "is_server"
        return False


def is_server_admin():
    """Decorator function handler
    """
    return commands.check(lambda ctx: is_server_admin_check(ctx.message))
