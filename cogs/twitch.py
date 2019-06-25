import asyncio
import os
import json

from discord.ext.commands import Cog

from .utils import models


class Twitch(Cog):
    def __init__(self, bot):
        self.bot = bot
        loop = self.bot.loop
        coro = self.wait_for_twitch_notif()
        self.future_reload_listener = asyncio.run_coroutine_threadsafe(
            coro, loop)

    async def wait_for_twitch_notif(self):
        path = os.path.dirname(os.path.abspath(__file__))
        twitch_notif_data = {}
        while True:
            is_file_exist = os.path.isfile(path + "/twitch_notif")
            if is_file_exist:
                with open(path + "/twitch_notif") as f:
                    twitch_notif_data = json.loads(f.read())
                await self.send_twitch_notif(twitch_notif_data)
                os.remove(path + "/twitch_notif")
            else:
                await asyncio.sleep(3)

    async def send_twitch_notif(self, twitch_notif_data):
        twitch_account = models.session.query(models.TwitchAccount).filter(
            models.TwitchAccount.twitch_id ==
            twitch_notif_data['data'][0]['user_id']
        )
        servers_linked = models.session.query(models.Server).filter(
            models.Server.twitch_account_linked == twitch_account.id
        ).all()
        for server_linked in servers_linked:
            message = "En live !" + \
                twitch_notif_data['data'][0]['user_name']
            channel_to_notif_id = server_linked.notification_channel_twitter
            guild = self.bot.get_guild(int(server_linked.server_id))
            for channel in guild.channels:
                if channel.id == int(channel_to_notif_id):
                    return await channel.send(message)


def setup(bot):
    bot.add_cog(Twitch(bot))
