import unittest.mock as mock
import asyncio
import discord
import tweepy

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest import TestCase


import cogs.twitter as twitter
import cogs.utils.models as models


def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper


class MockBot(discord.ext.commands.Bot):
    def __init__(self, cmd_prefix):
        self.command_prefix = cmd_prefix


class MockClientUser(discord.ClientUser):
    def __init__(self):
        self.id = 0


class MockState(discord.state.ConnectionState):
    def __init__(self):
        self.user = MockClientUser()


class MockUser(discord.User):
    def __init__(self):
        self.id = 0
        self.name = "testUser"
        self.bot = False


class MockMessage(discord.Message):
    def __init__(self, content, author, state):
        self.author = author
        self.content = content
        self.clean_content = content
        self._state = state
        self.attachments = []

    async def delete(self):
        pass


class MockGuild(discord.Guild):
    def __init__(self):
        self.id = 0
        self.name = "testGuild"


class MockCtx(discord.ext.commands.Context):
    def __init__(self, message):
        self.message = message
        self.guild = MockGuild()

    async def send(self, message):
        return message


class MockTweepyUser(tweepy.models.User):
    def __init__(self):
        self.id = 0
        self.id_str = "0"
        self.name = "twitter_test"


class MockTweepyStatus(tweepy.models.Status):
    def __init__(self, data):
        self._json = data


class MockTweepyAPI(tweepy.API):
    def __init__(self, auth):
        self.auth = auth

    def me(self):
        return MockTweepyUser()

    def update_status(self, tweet):
        data = {'id': 0, 'id_str': 'tweet_id'}
        return MockTweepyStatus(data)

    def destroy_status(self, id):
        pass


class MockTweepyStream(tweepy.Stream):
    def __init__(self, auth, listener):
        pass

    def filter(self, follow, is_async):
        pass


class TestCogsTwitter(TestCase):
    @mock.patch('tweepy.API',
                side_effect=MockTweepyAPI)
    @mock.patch('tweepy.Stream',
                side_effect=MockTweepyStream)
    def setUp(self, tweepy_api, tweepy_stream):
        self.bot = MockBot(cmd_prefix="!")
        models.engine = create_engine("sqlite:///:memory:")
        models.Session = sessionmaker(models.engine)
        models.session = models.Session()
        models.Base.metadata.create_all(models.engine)
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
            twitter_account_linked=tw_account.id
        )
        models.session.add(server)
        models.session.flush()
        self.twitter = twitter.Twitter(self.bot)

    @async_test
    async def test_tweet_func_without_media(self):
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
    async def test_tweet_delete_func(self):
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
