"""Tests for the cogs.twitter.py functions
"""
import asyncio
import json

import unittest.mock as mock
import discord
import tweepy
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest import TestCase


import cogs.twitter as twitter
import cogs.utils.models as models


def async_test(f):
    """Decorator to run a test asynchronously
    """
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


class MockBotBase(discord.ext.commands.bot.BotBase):
    """Mock the discord.ext.commands.BotBase class
    Used with discord.Client to make a Bot
    """

    def __init__(self):
        pass

    @property
    def cogs(self):
        return {}

    @property
    def loop(self):
        return ""


class MockBot(MockBotBase, discord.Client):
    """Mock the discord.ext.commands.Bot class
    Used to create a fake bot
    """

    def __init__(self):
        pass

    def get_guild(self, id):
        return MockGuild()


class MockClientUser(discord.ClientUser):
    """Mock the discord.ClientUser class
    Used to create a fake client user
    """

    def __init__(self):
        self.id = 0


class MockState(discord.state.ConnectionState):
    """Mock the discord.state.ConnectionState class
    Used to create a fake state
    """

    def __init__(self):
        self.user = MockClientUser()


class MockUser(discord.User):
    """Mock the discord.User class
    Used to create a fake User
    """

    def __init__(self):
        self.id = 0
        self.name = "testUser"
        self.bot = False


class MockChannel(discord.channel.TextChannel):
    """Mock the discord.channel.TextChannel class
    Used to create a fake Text Channel
    """

    def __init__(self, state, guild, id):
        self._state = state
        self.guild = guild
        self.id = id
        self.name = "twitter"

    async def send(self, message):
        return message


class MockAttachment(discord.Attachment):
    """Mock the discord.Attachment class
    Used to create a fake Attachment
    """

    def __init__(self, url):
        self.url = url


class MockMessage(discord.Message):
    """Mock the discord.Message class
    Used to create a fake Message
    """

    def __init__(self, content, author, state):
        self.author = author
        self.content = content
        self.clean_content = content
        self._state = state
        self.attachments = []

    async def delete(self):
        pass


class MockGuild(discord.Guild):
    """Mock the discord.Guild class
    Used to create a fake Guild
    """

    def __init__(self):
        self.id = 0
        self.name = "testGuild"
        self._channels = {'0': MockChannel(MockState(), self, 0)}


class MockCtx(discord.ext.commands.Context):
    """Mock the discord.ext.commands.Context class
    Used to create a fake context
    """

    def __init__(self, message):
        self.message = message
        self.guild = MockGuild()

    async def send(self, message):
        return message


class MockTweepyUser(tweepy.models.User):
    """Mock the tweepy.models.User class
    Used to create a fake tweepy user
    """

    def __init__(self):
        self.id = 0
        self.id_str = "0"
        self.name = "twitter_test"


class MockTweepyStatus(tweepy.models.Status):
    """Mock the tweepy.models.Status class
    Used to create a fake tweepy status
    """

    def __init__(self, data):
        self._json = data


class MockTweepyAPI(tweepy.API):
    """Mock the tweepy.API class
    Used to create a fake tweepy API
    """

    def __init__(self, auth):
        self.auth = auth

    def me(self):
        return MockTweepyUser()

    def update_status(self, tweet):
        data = {'id': 0, 'id_str': 'tweet_id'}
        return MockTweepyStatus(data)

    def destroy_status(self, id):
        pass

    def update_with_media(self, filename, status, file):
        data = {'id': 0, 'id_str': 'tweet_id',
                'entities': {'media': [{'media_url': 'media.url'}]}}
        return MockTweepyStatus(data)


class MockTweepyStream(tweepy.Stream):
    """Mock the tweepy.Stream class
    Used to create a fake tweepy Stream
    """

    def __init__(self, auth, listener):
        pass

    def filter(self, follow, is_async):
        pass


class MockStreamListener(twitter.MyStreamListener):
    """Mock the twitter.MyStreamListener class
    Used to create a fake MyStreamListener
    """

    def __init__(self, server_id, bot, api):
        self.bot = bot
        self.server_id = server_id


def mock_requests_get_video(url, allow_redirects=True):
    """Mock the requests.get function
    Arguments:
        Not Used

    Returns:
        requests.Responses with a header telling that response contains a video
    """
    resp = requests.Response()
    resp.headers['content-type'] = "video/mp4"
    type(resp).content = b'000000'
    return resp


def mock_requests_get_image(url, allow_redirects=True):
    """Mock the requests.get function
    Arguments:
        Not Used

    Returns:
        requests.Responses with a header telling that response contains a image
    """
    resp = requests.Response()
    resp.headers['content-type'] = "image/png"
    type(resp).content = b'000000'
    return resp


async def mock_twitter__twitter_post_media(ctx, content, video,
                                           content_type, content_extension):
    """Mock the twitter.Twitter._twitter_post_media function
    Arguments:
        Not Used

    Returns:
        media_id_string , auth
    """
    return 0, None


def mock_twitter__tweet_with_video(ctx, auth, tweet, username,
                                   media_id, media_url, tweet_object_content):
    """Mock the twitter.Twitter._tweet_with_video function
    Arguments:
        media_id
        Others Not Used

    Returns:
        tweet_object_content : dict
    """
    return {'media_id': media_id, 'type': 'video'}


def mock_twitter__tweet_with_image(ctx, auth, tweet, username,
                                   media_id, media_url, tweet_object_content):
    """Mock the twitter.Twitter._tweet_with_image function
    Arguments:
        media_id
        Others Not Used

    Returns:
        tweet_object_content : dict
    """
    return {'media_id': media_id, 'type': 'image'}


def mock_requests_post_video(url, auth, data):
    """
    Mock the requests.post function
    Arguments:
        Not Used

    Returns:
        requests.Response with data faking video post from twitter
    """
    resp = requests.Response()
    resp.status_code = 200
    data = json.dumps({'id': 0, 'id_str': 'tweet_id',
                       'extended_entities':
                       {'media': [{'video_info':
                                   {'variants': [
                                       {'bitrate': '5000',
                                        'url': 'bad_quality.url'},
                                       {
                                           'bitrate': '85000',
                                           'url': 'good_quality.url'}
                                   ]}}]}})
    type(resp).text = mock.PropertyMock(
        return_value=data
    )
    return resp


def mock_requests_post_media(url, auth, data):
    """
    Mock the requests.post function
    Arguments:
        Not Used

    Returns:
        requests.Response with data faking media post from twitter
    """
    resp = requests.Response()
    resp.status_code = 200
    if data['command'] == "INIT":
        json_data = json.dumps({'media_id_string': 'media.id'})
        type(resp).text = mock.PropertyMock(
            return_value=json_data
        )
        return resp
    else:
        pass


def mock_asyncio_run_coroutine_threadsafe(coro, loop):
    return True


class TestCogsTwitter(TestCase):
    """Tests for cogs.twitter.py
    """
    @mock.patch('tweepy.API',
                side_effect=MockTweepyAPI)
    @mock.patch('tweepy.Stream',
                side_effect=MockTweepyStream)
    @mock.patch('cogs.twitter.MyStreamListener',
                side_effect=MockStreamListener)
    @mock.patch('asyncio.run_coroutine_threadsafe',
                side_effect=mock_asyncio_run_coroutine_threadsafe)
    def setUp(self, tweepy_api,
              tweepy_stream, stream_listener, run_coroutine_threadsafe):
        """Setup for the tests
        """
        # Create a fake bot
        self.bot = MockBot()
        # Setup database
        models.engine = create_engine("sqlite:///:memory:")
        models.Session = sessionmaker(models.engine)
        models.session = models.Session()
        models.Base.metadata.create_all(models.engine)
        # Create database data
        user = models.User(
            discord_user_id="0",
        )
        models.session.add(user)
        models.session.flush()
        tw_account = models.TwitterAccount(
            user_id=user.id,
            twitter_name="twitter_test",
            access_token="test",
            access_secret='testsecret',
            account_user_id="0",
        )
        models.session.add(tw_account)
        models.session.flush()
        server = models.Server(
            server_id="0",
            server_name="testGuild",
            discord_admin_id="0",
            admin_id=user.id,
            twitter_account_linked=tw_account.id,
            twitter_notification_enabled=True,
            notification_channel_twitter="0"
        )
        models.session.add(server)
        models.session.flush()
        # Create Twitter object to access functions
        self.twitter = twitter.Twitter(self.bot)
        # Create fake streamListener object to ignore tweet reception
        self.streamListener = twitter.MyStreamListener("0", self.bot, None)

    # Unit tests

    def test__send_tweet_object_func(self):
        """Test the twitter.Twitter._send_tweet_object function
        This function is used to store new tweet data to database
        """
        tweet_object_content = {
            'tweet': 'testContent',
            'tweet_url': 'https://twitter.com/tweeter_test/status/5',
            'account_id': '0',
            'media_url': [],
            'is_send_by_bot': True
        }
        self.twitter._send_tweet_object(tweet_object_content)
        tweet_db = models.session.query(models.Tweet).filter(
            models.Tweet.tweet_url == tweet_object_content['tweet_url']
        ).first()
        tweet_media = tweet_db.media_id
        self.assertEqual(tweet_object_content['tweet'], tweet_db.tweet_content)
        self.assertEqual(
            tweet_object_content['media_url'], tweet_media)

    @async_test
    async def test__tweet_without_media_func(self):
        """Test the twitter.Twitter._tweet_without_media_func function
        This function is used to send tweet without media
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        ctx = MockCtx(message)
        tweet_object_content = await self.twitter._tweet_without_media(
            ctx, "test", MockTweepyAPI(""), "test_twitter_account", {}
        )
        self.assertEqual(
            tweet_object_content['tweet_url'],
            "https://twitter.com/test_twitter_account/status/tweet_id"
        )

    @async_test
    async def test__tweet_with_media_logic_video(self):
        """Test the twitter.Twitter._tweet_with_media_logic function
        This function is the logic behind sending a tweet with media
        This test focuses on the sending of a video
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        attachments = MockAttachment("url.media")
        message.attachments.append(attachments)
        ctx = MockCtx(message)
        with mock.patch('requests.get', side_effect=mock_requests_get_video):
            with mock.patch('cogs.twitter.Twitter._twitter_post_media',
                            side_effect=mock_twitter__twitter_post_media):
                with mock.patch('cogs.twitter.Twitter._tweet_with_video',
                                side_effect=mock_twitter__tweet_with_video):
                    tweet_object = await self.twitter._tweet_with_media_logic(
                        ctx, "test", MockTweepyAPI(
                            ""), "test_twitter_account", {}
                    )
                    self.assertEqual(tweet_object['type'], "video")

    @async_test
    async def test__tweet_with_media_logic_image(self):
        """Test the twitter.Twitter._tweet_with_media_logic function
        This function is the logic behind sending a tweet with media
        This test focuses on the sending of a image
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        attachments = MockAttachment("url.media")
        message.attachments.append(attachments)
        ctx = MockCtx(message)
        with mock.patch('requests.get', side_effect=mock_requests_get_image):
            with mock.patch('cogs.twitter.Twitter._twitter_post_media',
                            side_effect=mock_twitter__twitter_post_media):
                with mock.patch('cogs.twitter.Twitter._tweet_with_image',
                                side_effect=mock_twitter__tweet_with_image):
                    tweet_object = await self.twitter._tweet_with_media_logic(
                        ctx, "test", MockTweepyAPI(
                            ""), "test_twitter_account", "media.url",
                    )
                    self.assertEqual(tweet_object['type'], "image")

    @mock.patch('tweepy.API',
                side_effect=MockTweepyAPI)
    def test__tweet_with_image(self, tweepy_api):
        """Test the twitter.Twitter._tweet_with_image function
        This function is used to send tweet with a image
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        attachments = MockAttachment("url.media")
        message.attachments.append(attachments)
        ctx = MockCtx(message)
        media_request = mock_requests_get_image("media.url")
        tweet_object = self.twitter._tweet_with_image(
            ctx, "test", MockTweepyAPI(""),
            "test_twitter_account", "media.url",
            media_request, {}
        )
        self.assertEqual(
            tweet_object['tweet_url'],
            "https://twitter.com/test_twitter_account/status/tweet_id"
        )
        self.assertEqual(
            tweet_object['media_url'], "media.url"
        )

    @mock.patch('requests.post', side_effect=mock_requests_post_video)
    def test__tweet_with_video(self, requests_post_video):
        """Test the _tweet_with_video and the _get_best_bitrate_video functions
        This function is used to send tweet with a video
        This unit test contains a small integration to avoid to rewrite
        another test for the other function.
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        attachments = MockAttachment("url.media")
        message.attachments.append(attachments)
        ctx = MockCtx(message)
        tweet_object = self.twitter._tweet_with_video(
            ctx, None, "test", "test_twitter_account", 0, "media.url", {}
        )
        self.assertEqual(tweet_object['media_url'], "good_quality.url")

    @async_test
    async def test__twitter_post_media(self):
        """Test the twitter.Twitter._twitter_post_media function
        This function is used to post media to tweeter API
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        attachments = MockAttachment("url.media")
        message.attachments.append(attachments)
        ctx = MockCtx(message)
        with mock.patch('requests.post', side_effect=mock_requests_post_media):
            json_data = await self.twitter._twitter_post_media(
                ctx, b'0000000', b'0000000', "video", "mp4"
            )
            self.assertEqual(json_data[0], "media.id")

    # Integration tests

    @async_test
    async def test_tweet_func_without_media(self):
        """Test the twitter.Twitter.tweet_func function
        This function is used when command !tweet [text] is send
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        ctx = MockCtx(message)
        with mock.patch('tweepy.API',
                        side_effect=MockTweepyAPI):
            ret = await self.twitter.tweet_func(ctx)
            tweet = models.session.query(models.Tweet).first()
            self.assertIn("testUser", ret)
            self.assertIn("tweet_id", ret)
            self.assertEqual("testUser : test", tweet.tweet_content)

    @async_test
    async def test_tweet_func_without_account(self):
        """Test the tweet function
        This function is used when command !tweet [text] is send
        This is the main logic for sending a tweet
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        ctx = MockCtx(message)
        with mock.patch('tweepy.API',
                        side_effect=MockTweepyAPI):
            self.twitter.account = {}
            ret = await self.twitter.tweet_func(ctx)
            tweet = models.session.query(models.Tweet).first()
            self.assertIn("Aucun compte tweeter n'as été configuré !", ret)
            self.assertEqual(tweet, None)

    @async_test
    async def test_tweet_delete(self):
        """Test the twitter.Twitter.tweet_delete_func
        This function is used to delete a tweet from twitter and into the
        database
        """
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet test", author, state)
        ctx = MockCtx(message)
        with mock.patch('tweepy.API',
                        side_effect=MockTweepyAPI):
            await self.twitter.tweet_func(ctx)
            just_tweeted = models.session.query(models.Tweet).first()
            message = MockMessage(
                "!dTweet https://twitter.com/twitter_test/status/tweet_id",
                author,
                state)
            ctx = MockCtx(message)
            await self.twitter.tweet_delete_func(ctx)
            deleted_tweet = models.session.query(models.Tweet).first()
            self.assertNotEqual(just_tweeted, deleted_tweet)

    @mock.patch('cogs.twitter.MyStreamListener',
                side_effect=MockStreamListener)
    def test_new_tweet_received(self, stream_listener):
        data = {'id': '5',
                'user': {'id_str': '0', 'name': 'tweeter_test'},
                'text': 'testContent',
                'entities': {'media': [{'url': 'media.url'}]},
                'timestamp_ms': 1560244620806}
        status = MockTweepyStatus(data)
        tweet = self.streamListener.on_status(status)
        self.assertEqual(data['id'], tweet['tweet_id'])
        self.assertEqual(
            int(round(data['timestamp_ms'] / 1000)), tweet['timestamp'])

    @async_test
    async def test_get_tweet_not_in_db(self):
        tweet = {'tweet_id': '5',
                 'user_id': '0',
                 'username': 'tweeter_test',
                 'tweet_content': 'testContent',
                 'tweet_url': 'https://twitter.com/tweeter_test/status/5',
                 'medias_url': ['media.url'],
                 'timestamp': 1560244621}
        with mock.patch('tweepy.API',
                        side_effect=MockTweepyAPI):
            message = await self.twitter.get_tweet(tweet, 0)
            self.assertEqual(
                message,
                "Nouveau tweet : https://twitter.com/tweeter_test/status/5")

    @async_test
    async def test_get_tweet_func_already_in_db(self):
        tweet = {'tweet_id': '5',
                 'user_id': '0',
                 'username': 'tweeter_test',
                 'tweet_content': 'testContent',
                 'tweet_url': 'https://twitter.com/tweeter_test/status/5',
                 'medias_url': ['media.url'],
                 'timestamp': 1560244621}
        tweet_obj = models.Tweet(
            tweet_url='https://twitter.com/tweeter_test/status/5',
            tweet_content='testContent_old'
        )
        models.session.add(tweet_obj)
        with mock.patch('tweepy.API',
                        side_effect=MockTweepyAPI):
            message = await self.twitter.get_tweet(tweet, 0)
            self.assertEqual(
                message,
                "Nouveau tweet : https://twitter.com/tweeter_test/status/5")
        tweet_db = models.session.query(models.Tweet).filter(
            models.Tweet.tweet_url == tweet['tweet_url']
        ).first()
        self.assertNotEqual(tweet['tweet_content'], tweet_db.tweet_content)
        self.assertEqual(tweet_obj.id, tweet_db.id)
        self.assertEqual(tweet_obj.tweet_content, tweet_db.tweet_content)
