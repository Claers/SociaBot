"""Twitter module for SociaBot discord bot

"""
from datetime import datetime
from io import BytesIO
import tweepy
import requests
import asyncio
import base64
import math
from requests_oauthlib import OAuth1


from discord.ext.commands import Cog
from discord.ext import commands

from .utils import checks
from .utils import models
from .utils import settings


class Twitter(Cog):

    def __init__(self, bot):
        """Init for the Twitter Cog

        Arguments:
            bot {DiscordBot} -- Reference to the bot

        Keyword Arguments:
            account {dict} -- empty twitter account dict init (default: {})
        """
        self.bot = bot
        self.account = {}
        self.streamListener = {}
        self.stream = {}
        self.__twitter_account_setup()
        self.future_tweet_listener = None

    def __twitter_account_setup(self):
        """Load all twitter account configured in the database into a list of
        tweepy objects
        """
        accounts = models.session.query(models.TwitterAccount).all()
        for taccount in accounts:
            server_id = models.session.query(
                models.Server).get(
                    taccount.server_id).server_id
            self.account[server_id] = tweepy.OAuthHandler(
                settings.TwitterKey,
                settings.TwitterSecret, 'oob')
            self.account[server_id] .set_access_token(
                taccount.access_token, taccount.access_secret)
            api = tweepy.API(self.account[server_id])
            id = api.me().id_str
            self.streamListener[server_id] = MyStreamListener(
                server_id, self.bot, api)
            self.stream[server_id] = tweepy.Stream(
                auth=api.auth,
                listener=self.streamListener[server_id])
            self.stream[server_id].filter(follow=[id], is_async=True)

    def loop_handle(self, tweet, server_id):
        loop = self.bot.loop
        coro = self.get_tweet(tweet, server_id)
        self.future_tweet_listener = asyncio.run_coroutine_threadsafe(
            coro, loop)

    async def get_tweet(self, tweet, server_id):
        guild = self.bot.get_guild(int(server_id))
        for channel in guild.channels:
            if channel.name == "twitter":
                await channel.send(tweet)

    @commands.command()
    @checks.is_server()
    async def tweet(self, ctx):
        tweet = ctx.message.clean_content.replace(
            '!tweet', '{0} :'.format(ctx.author.name))
        api = tweepy.API(self.account[str(ctx.guild.id)])
        username = api.me().name
        server = models.session.query(models.Server).filter(
            models.Server.server_id == str(ctx.guild.id)).first()
        print(server)
        tweet_object_content = {}
        tweet_object_content['tweet'] = tweet
        tweet_object_content['account_id'] = server.twitter_account_id
        )
        if len(ctx.message.attachments) == 1:
            tweet_object_content=await self.__tweet_with_media_logic(
                ctx, tweet, api, username, server, tweet_object_content
            )
        elif len(ctx.message.attachments) > 1:
            tweet_object_content = await self.__tweet_with_multiple_media(
                ctx, tweet, api, username, server, tweet_object_content
            )
        else:
            tweet_object_content = await self.__tweet_without_media(
                ctx, tweet, api, username, server, tweet_object_content
            )
        await self.__send_tweet_object(tweet_object_content)
        await ctx.send(
            "Bravo {0} ! Votre tweet a été envoyé : ".format(
                ctx.author.name)
            + tweet_object_content['tweet_url'])
        await ctx.message.delete()

    async def __send_tweet_object(self, tweet_object_content):
        tweet_object = models.Tweet(
            tweet_content=tweet_object_content['tweet'],
            tweet_url=tweet_object_content['tweet_url'],
            tweet_date=datetime.now(),
            twitter_account_id=tweet_object_content['account_id']
        )
        models.session.add(tweet_object)
        models.session.flush()
        if tweet_object_content['media_url'] != "":
            media_object = models.TweetMedia(
                media_url=tweet_object_content['media_url']
            )
            models.session.add(media_object)
            models.session.flush()
            tweet_object.media_id.append(media_object)
        elif type(tweet_object_content['media_url']) == list:
            for media_url in tweet_object_content['media_url']:
                media_object = models.TweetMedia(
                    media_url=tweet_object_content['media_url']
                )
                models.session.add(media_object)
                models.session.flush()
                tweet_object.media_id.append(media_object)
        models.session.flush()
        models.session.commit()

    async def __tweet_without_media(self, ctx, tweet, api,
                                    username, server, tweet_object_content):
        tweetJson = api.update_status(tweet)
        tweet_id = tweetJson._json['id_str']
        tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                tweet_id)
        tweet_object_content['tweet_url'] = tweet_url
        tweet_object_content['media_url'] = ""
        return tweet_object_content

    async def __tweet_with_media_logic(
            self, ctx, tweet, api, username, server, tweet_object_content):
        media_url = ctx.message.attachments[0].url
        media_request = requests.get(media_url, allow_redirects=True)
        content_type, content_extension = media_request.headers.get(
            "content-type").split('/')
        if content_type == "video":
            video = base64.b64encode(media_request.content)
            if len(video) < 15000000:
                media_id, auth = await self.__twitter_post_media(
                    ctx, media_request.content, video,
                    content_type, content_extension
                )
                tweet_object_content = await self.__tweet_with_video(
                    ctx, auth, tweet, username,
                    server, media_id, media_url, tweet_object_content
                )
        elif content_type == "image":
            if content_extension == "GIF":
                if len(media_request.content) < 15000000:
                    tweet_object_content = await self.__tweet_with_image(
                        ctx, tweet, api, username,
                        server, media_url, media_request, tweet_object_content
                    )
            else:
                if len(media_request.content) < 5000000:
                    tweet_object_content = await self.__tweet_with_image(
                        ctx, tweet, api, username,
                        server, media_url, media_request, tweet_object_content
                    )
        return tweet_object_content

    async def __tweet_with_image(
            self, ctx, tweet, api, username, server, media_url,
            media_request, tweet_object_content):
        content_type, content_extension = media_request.headers.get(
            "content-type").split('/')
        tweetJson = api.update_with_media(
            "media." + content_extension, status=tweet,
            file=BytesIO(media_request.content)
        )
        tweet_id = tweetJson._json['id_str']
        tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                tweet_id)
        media_url = tweetJson._json['entities']['media'][0]['media_url']
        tweet_object_content['tweet_url'] = tweet_url
        tweet_object_content['media_url'] = media_url
        return tweet_object_content

    async def __tweet_with_video(
            self, ctx, auth, tweet,
            username, server, media_id, media_url, tweet_object_content):
        url = 'https://api.twitter.com/1.1/statuses/update.json'
        response = requests.post(
            url, auth=auth, data={
                "status": tweet,
                "media_ids": [media_id]
            }
        )
        videos_url = response.json(
        )['extended_entities']['media'][0]['video_info']['variants']
        video_url = await self.__get_best_bitrate_video(videos_url)
        tweet_id = response.json()['id']
        tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                tweet_id)
        tweet_object_content['tweet_url'] = tweet_url
        tweet_object_content['media_url'] = video_url
        return tweet_object_content

    async def __get_best_bitrate_video(self, json):
        maxbitrate = 0
        url = ""
        for video in json:
            if 'bitrate' in video:
                if maxbitrate < video['bitrate']:
                    url = video['url']
        return url

    async def __divide_vid_in_chunk(self, chunk, video):
        """Function used to divide a video (or any valid data) bigger than 1Mo to chunk

        Arguments:
            chunk {int} -- The actual chunk of the data to return
            video {bytes} -- The data to chunk

        Returns:
            data {bytes} -- The data chunked ready to be sent
        """
        mil = 1000000
        if(chunk == 0):
            return (video[:1*mil])
        else:
            return (video[chunk*mil:(chunk+1)*mil])

    async def __twitter_post_media(
            self, ctx, raw_vid, media, content_type, content_extension):
        media_len_MB = len(media)/1000000
        url = 'https://upload.twitter.com/1.1/media/upload.json'
        auth = OAuth1(settings.TwitterKey, settings.TwitterSecret,
                      self.account[str(ctx.guild.id)].access_token,
                      self.account[str(ctx.guild.id)].access_token_secret
                      )
        if(content_type == "image"):
            response = requests.post(
                url, auth=auth, data={
                    "media_data": media}
            )
            return response.json()["media_id_string"]
        else:
            response = requests.post(
                url, auth=auth, data={
                    "command": "INIT",
                    "total_bytes": str(len(raw_vid)),
                    "media_type": content_type + "/" + content_extension
                }
            )
            if(media_len_MB < 1):
                requests.post(
                    url, auth=auth, data={
                        "command": "APPEND",
                        "media_id": response.json()['media_id_string'],
                        "media_data": media,
                        "segment_index": "0"}
                )
                await asyncio.sleep(3)
            else:
                for i in range(math.ceil(media_len_MB)):
                    requests.post(
                        url, auth=auth, data={
                            "command": "APPEND",
                            "media_id": response.json()['media_id_string'],
                            "media_data": await self.__divide_vid_in_chunk(
                                i, media
                            ),
                            "segment_index": i}
                    )
                await asyncio.sleep(5)
            requests.post(
                url, auth=auth, data={
                    "command": "FINALIZE",
                    "media_id": response.json()['media_id_string'],
                }
            )
            return response.json()["media_id_string"], auth

    async def __tweet_with_multiple_media(
            self, ctx, tweet, api, username, server):
        medias_id = []
        for attachements in ctx.message.attachements:
            media_id, auth = await self.__twitter_post_media(
                ctx, media_request.content, video,
                content_type, content_extension
            )
            medias_id.append(media_id)
        url = 'https://api.twitter.com/1.1/statuses/update.json'
        response = requests.post(
            url, auth=auth, data={
                "status": tweet,
                "media_ids": medias_id
            }
        )
        videos_url = response.json(
        )['extended_entities']['media'][0]['video_info']['variants']
        video_url = await self.__get_best_bitrate_video(videos_url)
        tweet_id = response.json()['id']
        tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                tweet_id)
        tweet_object_content['tweet_url'] = tweet_url
        tweet_object_content['media_url'] = video_url
        return tweet_object_content

    @commands.command(name="deleteTweet")
    @checks.is_server()
    @checks.is_server_admin()
    async def tweet_delete(self, ctx):
        tweetURL = ctx.message.clean_content.replace('!deleteTweet ', '')
        tweet_object = models.session.query(
            models.Tweet).filter(models.Tweet.tweet_url ==
                                 tweetURL).first()
        medias = tweet_object.media_id
        for media in medias:
            models.session.delete(media)
            models.session.flush()
        models.session.delete(tweet_object)
        models.session.flush()
        models.session.commit()
        api = tweepy.API(self.account[str(ctx.guild.id)])
        username = api.me().name
        tweetID = tweetURL.replace(
            "https://twitter.com/{0}/status/".format(username), '')
        tweetID = "".join(tweetID.split())
        api.destroy_status(tweetID)
        await ctx.send(
            "Bravo {0} ! Votre tweet a été supprimé !".format(ctx.author.name))
        await ctx.message.delete()


class MyStreamListener(tweepy.StreamListener):

    def __init__(self, server_id, bot, api):
        self.server_id = server_id
        self.bot = bot
        super().__init__(api=api)

    def on_status(self, status):
        tweet_id = status._json['id']
        username = status._json['user']['name']
        tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                tweet_id)
        tweet = "Nouveau tweet : " + tweet_url
        self.bot.cogs['Twitter'].loop_handle(
            tweet, self.server_id)


def setup(bot):
    bot.add_cog(Twitter(bot))
