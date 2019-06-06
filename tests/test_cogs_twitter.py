import unittest.mock as mock
import asyncio
import discord

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


class MockBotBase(discord.ext.commands.BotBase):
    def setTest(self, user):
        pass


class MockClientUser(discord.ClientUser):
    def __init__(self):
        self.id = 0


class MockState(discord.state.ConnectionState):
    def __init__(self):
        self.user = MockClientUser()


class MockClient(discord.Client):
    def __init__(self):
        self._connection = MockState()


class MockBot(MockBotBase, MockClient):
    def setTest(self, user):
        pass


class MockUser(discord.User):
    def __init__(self):
        self.id = 0
        self.name = "test"
        self.bot = False


class MockMessage(discord.Message):
    def __init__(self, message, author, state):
        self.author = author
        self.content = message
        self.clean_content = message
        self._state = state


class TestCogsTwitter(TestCase):
    def setUp(self):
        self.bot = MockBot(command_prefix="!")
        self.bot.load_extension("cogs.twitter")
        self.twitter = twitter.Twitter(self.bot)
        models.engine = create_engine("sqlite:///:memory:")
        models.Session = sessionmaker(models.engine)
        models.session = models.Session()
        models.Base.metadata.create_all(models.engine)

    @async_test
    async def test_tweet(self):
        state = MockState()
        author = MockUser()
        message = MockMessage("!tweet", author, state)
        ret = await self.twitter.test()
        self.assertTrue(ret)
