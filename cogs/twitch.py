import asyncio
import os
import json

from discord.ext.commands import Cog


class Twitch(Cog):
    def __init__(self, bot):
        self.bot = bot
        loop = self.bot.loop
        coro = self.wait_for_twitch_notif()
        self.future_reload_listener = asyncio.run_coroutine_threadsafe(
            coro, loop)

    async def wait_for_twitch_notif(self):
        twitch_notif_data = {}
        while True:
            is_file_exist = os.path.isfile("./twitch_notif")
            if is_file_exist:
                with open("twitch_notif") as f:
                    twitch_notif_data = json.loads(f)
                print(twitch_notif_data)
                os.remove("./twitch_notif")
            else:
                await asyncio.sleep(3)


def setup(bot):
    bot.add_cog(Twitch(bot))
