from discord.ext import commands
from .utils import checks
from .utils import models
from .utils import settings
import tweepy
from discord.ext.commands import Cog


class Config(Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.is_server_admin()
    async def config(self, ctx):
        await ctx.author.send(
            "Bienvenue dans la configuration " +
            "de votre serveur pour SociaBot {}\n".format(ctx.author.mention))
        self.bot.cogs['Twitter'].account[ctx.guild.id] = tweepy.OAuthHandler(
            settings.TwitterKey,
            settings.TwitterSecret, 'oob')
        auth_url = self.bot.cogs['Twitter'].account[
            ctx.guild.id].get_authorization_url(
        )
        await ctx.author.send("Cliquer sur ce lien pour autoriser" +
                              "l'application sur votre compte Twitter" +
                              auth_url)
        await ctx.author.send(
            "Entrer la commande !twitterConf {} ".format(ctx.guild.id) +
            "suivi du code fourni par Twitter pour finaliser la configuration."
        )

    @commands.command()
    @checks.is_private()
    async def twitterConf(self, ctx):
        message = ctx.message.content.split()
        if(len(message) == 3):
            server = models.session.query(
                models.Server).filter(models.Server.server_id ==
                                      str(message[1])).first()
            self.bot.cogs['Twitter'].account[int(message[1])].get_access_token(
                message[2])
            account = models.TwitterAccount(
                server_id=int(server.id),
                admin_id=server.admin_id,
                twitter_name=tweepy.API(self.bot.cogs['Twitter'].account[
                    int(message[1])]).me().name,
                access_token=self.bot.cogs['Twitter'].account[
                    int(message[1])
                ].access_token,
                access_secret=self.bot.cogs['Twitter'].account[
                    int(message[1])
                ].access_token_secret
            )
            models.session.add(account)
            models.session.flush()
            server.twitter_account_id = account.id
            models.session.commit()

        else:
            await ctx.author.send(
                "Erreur dans la commande, merci d'entrer la commande donnée " +
                "avec le code donné par Twitter.")


def setup(bot):
    bot.add_cog(Config(bot))
