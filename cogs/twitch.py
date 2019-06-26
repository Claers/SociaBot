import asyncio
import os
import json

from discord.ext.commands import Cog

from .utils import models


class Twitch(Cog):
    def __init__(self, bot):
        """Init for the Twitch Cog

        Arguments:
            bot {DiscordBot} -- Reference to the bot
        """
        self.bot = bot
        loop = self.bot.loop
        coro = self.wait_for_twitch_notif()
        self.future_reload_listener = asyncio.run_coroutine_threadsafe(
            coro, loop)

    async def wait_for_twitch_notif(self):
        """The handler waiting for new twitch notification
        It check into database if a webhook notif is set to True
        """
        while True:
            webhooks = models.session.query(
                models.TwitchAccountWebhook
            ).filter(
                models.TwitchAccountWebhook.new_notif == True
            ).all()
            for webhook in webhooks:
                webhook.new_notif = False
                models.session.commit()
                await self.send_twitch_notif(webhook)
            else:
                await asyncio.sleep(1)

    async def send_twitch_notif(self, webhook):
        """This function send the notification to the channel registered into
        database

        Arguments:
            webhook {models.TwitchAccountWebhook} -- The webhook object from db
        """
        twitch_account = models.session.query(models.TwitchAccount).filter(
            models.TwitchAccount.twitch_id ==
            webhook.twitch_id
        ).first()
        server_linked = models.session.query(models.Server).filter(
            models.Server.server_id == webhook.server_id
        ).first()
        message = "@everyone " + "En live ! https://twitch.tv/" + \
            twitch_account.twitch_name
        channel_to_notif_id = server_linked.notification_channel_twitch
        guild = self.bot.get_guild(int(webhook.server_id))
        if channel_to_notif_id is not None:
            for channel in guild.channels:
                if channel.id == int(channel_to_notif_id):
                    return await channel.send(message)
        else:
            message = message + " (CE MESSAGE A ÉTÉ ENVOYÉ ICI PAR DEFAUT)"
            return await guild.channels[0].send()


def setup(bot):
    bot.add_cog(Twitch(bot))
