from discord.ext import commands
from .utils import checks
from discord.ext.commands import Cog


class Testing(Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Hello {}".format(ctx.author.mention))

    @commands.command()
    @checks.is_private()
    async def test(self, ctx):
        await ctx.send("Hello {}".format(ctx.author.mention))


def setup(bot):
    bot.add_cog(Testing(bot))
