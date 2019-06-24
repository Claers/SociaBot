"""Twitter module for SociaBot discord bot
"""
from datetime import datetime
from io import BytesIO
import asyncio
import base64
import math
import json
import os

import tweepy
from requests_oauthlib import OAuth1
import requests
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
        self._twitter_account_setup()
        self.future_tweet_listener = None
        loop = self.bot.loop
        coro = self.wait_for_reload_config()
        self.future_reload_listener = asyncio.run_coroutine_threadsafe(
            coro, loop)

    def _twitter_account_setup(self):
        """Load all twitter account configured in the database into a list of
        tweepy objects
        """
        # Get all servers in database
        servers = models.session.query(models.Server).all()
        for server in servers:
            server_id = server.server_id
            self.account[server_id] = tweepy.OAuthHandler(
                settings.twitter_key,
                settings.twitter_secret, 'oob')
            # Get the twitter account linked to server
            tw_account = models.session.query(models.TwitterAccount).filter(
                models.TwitterAccount.id == server.twitter_account_linked
            ).first()
            if tw_account is not None:
                self.account[server_id].set_access_token(
                    tw_account.access_token, tw_account.access_secret)
                api = tweepy.API(self.account[server_id])
                id = api.me().id_str
                self.streamListener[server_id] = MyStreamListener(
                    server_id, self.bot, api)
                self.stream[server_id] = tweepy.Stream(
                    auth=api.auth,
                    listener=self.streamListener[server_id])
                self.stream[server_id].filter(follow=[id], is_async=True)

    async def wait_for_reload_config(self):
        """A function used to wait for a file to tell when reload variables
        """
        while True:
            is_file_exist = os.path.isfile("./need_to_reload")
            if is_file_exist:
                self._twitter_account_setup()
                os.remove("./need_to_reload")
            else:
                await asyncio.sleep(3)

    def loop_handle(self, tweet, server_id):
        """Used to start a coroutine when receiving tweet
        """
        loop = self.bot.loop
        coro = self.get_tweet(tweet, server_id)
        self.future_tweet_listener = asyncio.run_coroutine_threadsafe(
            coro, loop)

    async def get_tweet(self, tweet, server_id):
        """Handling data when getting tweet
        """
        channel_to_notif_id = models.session.query(models.Server).filter(
            models.Server.server_id == server_id
        ).first().notification_channel_twitter
        guild = self.bot.get_guild(int(server_id))
        for channel in guild.channels:
            if channel.id == int(channel_to_notif_id):
                return await channel.send("Nouveau tweet : " +
                                          tweet['tweet_url'])

    def _send_tweet_object(self, tweet_object_content,
                           datetime=datetime.now()):
        """This function is used to store new tweet data to database

        Arguments :
            tweet_object_content : dict of tweet data
            optional datetime : Custom time or datetime.now() by default
        """
        tweet_object = models.Tweet(
            tweet_content=tweet_object_content['tweet'],
            tweet_url=tweet_object_content['tweet_url'],
            tweet_date=datetime,
            twitter_account_id=tweet_object_content['account_id'],
            is_send_by_bot=tweet_object_content['is_send_by_bot']
        )
        models.session.add(tweet_object)
        models.session.flush()
        if type(tweet_object_content['media_url']) == list:
            for media_url in tweet_object_content['media_url']:
                media_object = models.TweetMedia(
                    media_url=media_url
                )
                models.session.add(media_object)
                models.session.flush()
                tweet_object.media_id.append(media_object)
        models.session.flush()
        models.session.commit()

    async def _tweet_without_media(self, ctx, tweet, api,
                                   username, tweet_object_content):
        """This function is used to send tweet without media

        Arguments:
            ctx : The context of the command
            tweet : The tweet string
            api : The OAuth1 api initialized
            username : The username of the twitter account
            tweet_object_content : Tweet data

        Returns:
            tweet_object_content : Tweet data
        """
        tweetJson = api.update_status(tweet)
        tweet_id = tweetJson._json['id_str']
        tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                tweet_id)
        tweet_object_content['tweet_url'] = tweet_url
        tweet_object_content['media_url'] = ""
        return tweet_object_content

    async def _tweet_with_media_logic(
            self, ctx, tweet, api, username, tweet_object_content):
        """This function is the logic behind sending a tweet with media

        Arguments:
            ctx : The context of the command
            tweet : The tweet string
            api : The OAuth1 api initialized
            username : The username of the twitter account
            tweet_object_content : Tweet data

        Returns:
            tweet_object_content : Tweet data
        """
        media_url = ctx.message.attachments[0].url
        media_request = requests.get(media_url, allow_redirects=True)
        content_type, content_extension = media_request.headers.get(
            "content-type").split('/')
        if content_type == "video":
            video = base64.b64encode(media_request.content)
            if len(video) < 15000000:
                media_id, auth = await self._twitter_post_media(
                    ctx, media_request.content, video,
                    content_type, content_extension
                )
                tweet_object_content = self._tweet_with_video(
                    ctx, auth, tweet, username,
                    media_id, media_url, tweet_object_content
                )
        elif content_type == "image":
            if content_extension == "GIF":
                if len(media_request.content) < 15000000:
                    tweet_object_content = self._tweet_with_image(
                        ctx, tweet, api, username,
                        media_url, media_request, tweet_object_content
                    )
            else:
                if len(media_request.content) < 5000000:
                    tweet_object_content = self._tweet_with_image(
                        ctx, tweet, api, username,
                        media_url, media_request, tweet_object_content
                    )
        else:
            tweet_object_content = await self._tweet_without_media(
                ctx, tweet, api, username, tweet_object_content
            )
        return tweet_object_content

    def _tweet_with_image(
            self, ctx, tweet, api, username, media_url,
            media_request, tweet_object_content):
        """This function is used to send tweet with a image

        Arguments:
            ctx : The context of the command
            tweet : The tweet string
            api : The OAuth1 api initialized
            username : The username of the twitter account
            media_url : The image url
            media_request : The media request (used to get content-type header)
            tweet_object_content : Tweet data

        Returns:
            tweet_object_content : Tweet data
        """
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

    def _tweet_with_video(
            self, ctx, auth, tweet,
            username, media_id, media_url, tweet_object_content):
        """This function is used to send tweet with a video

        Arguments:
            ctx : The context of the command
            auth : The OAuth1 api initialized
            tweet : The tweet string
            username : The username of the twitter account
            media_url : The image url
            media_request : The media request (used to get content-type header)
            tweet_object_content : Tweet data

        Returns:
            tweet_object_content : Tweet data
        """
        url = 'https://api.twitter.com/1.1/statuses/update.json'
        response = requests.post(
            url, auth=auth, data={
                "status": tweet,
                "media_ids": [media_id]
            }
        )
        json_data = json.loads(response.text)
        videos_url = json_data[
            'extended_entities']['media'][0]['video_info']['variants']
        video_url = self._get_best_bitrate_video(videos_url)
        tweet_id = json_data['id']
        tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                tweet_id)
        tweet_object_content['tweet_url'] = tweet_url
        tweet_object_content['media_url'] = video_url
        return tweet_object_content

    def _get_best_bitrate_video(self, json):
        """This function is used to get the best video based on bitrate from
        a json list

        Arguments:
            json : The json containing videos

        Returns:
            url : The best bitrate video url
        """
        maxbitrate = 0
        url = ""
        for video in json:
            if 'bitrate' in video:
                if maxbitrate < int(video['bitrate']):
                    url = video['url']
        return url

    def _divide_vid_in_chunk(self, chunk, video):
        """Function used to divide a video (or any valid data) bigger than 1Mo to chunk

        Arguments:
            chunk : The actual number of chunk data to return
            video : The data to chunk

        Returns:
            data : The data chunked ready to be sent
        """
        mil = 1000000
        if(chunk == 0):
            return (video[:1*mil])
        else:
            return (video[chunk*mil:(chunk+1)*mil])

    async def _twitter_post_media(
            self, ctx, raw_vid, media, content_type, content_extension):
        """This function is used to post media to tweeter API

        Arguments:
            ctx : The context of the command
            raw_vid : The raw media
            media : The media encoded in base64
            content_type : The content type (video or image)
            content_extension : The content extension

        Returns:
            media_id_string : The media id
            auth : OAuth1 initialized
        """
        media_len_MB = len(media)/1000000
        url = 'https://upload.twitter.com/1.1/media/upload.json'
        auth = OAuth1(settings.twitter_key, settings.twitter_secret,
                      self.account[str(ctx.guild.id)].access_token,
                      self.account[str(ctx.guild.id)].access_token_secret
                      )
        response = requests.post(
            url, auth=auth, data={
                "command": "INIT",
                "total_bytes": str(len(raw_vid)),
                "media_type": content_type + "/" + content_extension
            }
        )
        json_data = json.loads(response.text)
        if(media_len_MB < 1):
            requests.post(
                url, auth=auth, data={
                    "command": "APPEND",
                    "media_id": json_data['media_id_string'],
                    "media_data": media,
                    "segment_index": "0"}
            )
            await asyncio.sleep(3)
        else:
            # If media lenght is greater that 1MB cut and
            # send it in chunk of 1MB
            for i in range(math.ceil(media_len_MB)):
                requests.post(
                    url, auth=auth, data={
                        "command": "APPEND",
                        "media_id": json_data['media_id_string'],
                        "media_data": await self._divide_vid_in_chunk(
                            i, media
                        ),
                        "segment_index": i}
                )
            await asyncio.sleep(5)
        requests.post(
            url, auth=auth, data={
                "command": "FINALIZE",
                "media_id": json_data['media_id_string'],
            }
        )
        return json_data["media_id_string"], auth

    async def tweet_func(self, ctx):
        """This is the main logic for sending a tweet
        """
        tweet = ctx.message.clean_content.replace(
            '!tweet', '{0} :'.format(ctx.author.name))
        try:
            api = tweepy.API(self.account[str(ctx.guild.id)])
        except KeyError:
            return await ctx.send("Aucun compte tweeter n'as été configuré !")
        username = api.me().name
        server = models.session.query(models.Server).filter(
            models.Server.server_id == str(ctx.guild.id)).first()
        tweet_object_content = {}
        tweet_object_content['tweet'] = tweet
        tweet_object_content['account_id'] = server.twitter_account_linked
        tweet_object_content['is_send_by_bot'] = True
        # If message have attachment
        if len(ctx.message.attachments) == 1:
            tweet_object_content = await self._tweet_with_media_logic(
                ctx, tweet, api, username, tweet_object_content
            )
        else:
            tweet_object_content = await self._tweet_without_media(
                ctx, tweet, api, username, tweet_object_content
            )
        # Store tweet data into database
        self._send_tweet_object(tweet_object_content)
        await ctx.message.delete()
        return await ctx.send(
            "Bravo {0} ! Votre tweet a été envoyé : ".format(
                ctx.author.name)
            + tweet_object_content['tweet_url'])

    @commands.command()
    @checks.is_server()
    async def tweet(self, ctx):
        """This function is used when command !tweet [text] is send
        """
        await self.tweet_func(ctx)

    async def tweet_delete_func(self, ctx):
        """This function is used to delete a tweet from twitter and into the
        database
        """
        tweetURL = ctx.message.clean_content.replace('!dTweet ', '')
        tweet_object = models.session.query(
            models.Tweet).filter(models.Tweet.tweet_url ==
                                 tweetURL).first()
        if tweet_object is not None:
            medias = tweet_object.media_id
            for media in medias:
                models.session.delete(media)
                models.session.flush()
            models.session.delete(tweet_object)
            models.session.flush()
            models.session.commit()
        try:
            api = tweepy.API(self.account[str(ctx.guild.id)])
            username = api.me().name
            tweetID = tweetURL.replace(
                "https://twitter.com/{0}/status/".format(username), '')
            tweetID = "".join(tweetID.split())
            api.destroy_status(tweetID)
            await ctx.send(
                "Bravo {0} ! Votre tweet a été supprimé !".format(
                    ctx.author.name))
            await ctx.message.delete()
        except tweepy.TweepError:
            await ctx.send('\N{WARNING SIGN} ' +
                           "Le tweet n'as pas été trouvé")
            await ctx.message.delete()

    @commands.command(name="dTweet")
    @checks.is_server()
    @checks.is_server_admin()
    async def tweet_delete(self, ctx):
        """This function is used when command !dTweet [tweet url or tweet id]
        is send
        """
        await self.tweet_delete_func(ctx)


class MyStreamListener(tweepy.StreamListener):

    def __init__(self, server_id, bot, api):
        self.server_id = server_id
        self.bot = bot
        super().__init__(api=api)

    def on_status(self, status):
        """This function is called when a status is created on the twitter
        account of the user
        """
        server = models.session.query(models.Server).filter(
            models.Server.server_id == self.server_id
        ).first()
        if server.twitter_notification_enabled:
            tweet_id = status._json['id']
            user_id = status._json['user']['id_str']
            username = status._json['user']['name']
            tweet_url = "https://twitter.com/{0}/status/{1}".format(username,
                                                                    tweet_id)
            tweet_content = status._json['text']
            timestamp = status._json['timestamp_ms']
            timestamp = int(round(int(timestamp) / 1000))
            try:
                status._json['retweeted_status']
                is_retweet = True
            except KeyError:
                is_retweet = False
            if server.retweet_activated is not None:
                if is_retweet is True and server.retweet_activated is False:
                    return "stop"
            medias_url = []
            if 'media' in status._json['entities']:
                for media in status._json['entities']['media']:
                    medias_url.append(media['url'])
            tweet = {'tweet_id': tweet_id,
                     'user_id': user_id,
                     'username': username,
                     'tweet_content': tweet_content,
                     'tweet_url': tweet_url,
                     'medias_url': medias_url,
                     'timestamp': timestamp}
            twitter_account = models.session.query(
                models.TwitterAccount).filter(
                models.TwitterAccount.account_user_id == tweet['user_id']
            ).first()
            tweet_db = models.session.query(models.Tweet).filter(
                models.Tweet.tweet_url == tweet['tweet_url']
            ).first()
            if tweet_db is None:
                tweet_object = {
                    'tweet': tweet['tweet_content'],
                    'tweet_url': tweet['tweet_url'],
                    'account_id': twitter_account.id,
                    'media_url': tweet['medias_url'],
                    'is_send_by_bot': False
                }
                if 'Twitter' in self.bot.cogs:
                    self.bot.cogs['Twitter']._send_tweet_object(
                        tweet_object, datetime.fromtimestamp(tweet['timestamp']
                                                             ))
                else:
                    tweet_db = ""
            while tweet_db is None:
                tweet_db = models.session.query(models.Tweet).filter(
                    models.Tweet.tweet_url == tweet['tweet_url']
                ).first()
            if 'Twitter' in self.bot.cogs and not tweet_db.is_send_by_bot:
                self.bot.cogs['Twitter'].loop_handle(
                    tweet, self.server_id)
            else:
                return tweet


def setup(bot):
    bot.add_cog(Twitter(bot))
