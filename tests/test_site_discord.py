"""Tests for the utils.discord_functions.py functions
"""
import requests_oauthlib
import unittest.mock as mock
import flask
import json

from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from requests.models import Response

import utils.discord_functions as discord_funcs
import cogs.utils.models as models
import website


def mock_oauth_authorization_url(url):
    """Mock the OAuth2Session.authorization_url function
    Return url and state for testing
    """
    return "discord.login.url", "000"


def mock_user_infos(discord_auth):
    """Mock the utils.discord_functions.user_infos function
    Return user infos for testing
    """
    return {'id': '0'}


def mock_oauth2_get(url):
    """Mock the OAuth2Session.get
    Return Response with json data
    """
    resp = Response()
    resp.status_code = 200
    data = json.dumps([{'id': '0', 'owner': True},
                       {'id': '1', 'owner': False}])
    type(resp).text = mock.PropertyMock(
        return_value=data
    )
    return resp


class TestDiscordUtilsFunctions(TestCase):
    """Tests for the discord functions contained in utils/discord_functions.py
    These functions are used in the website for authentification and other
    functionnalities
    """

    def setUp(self):
        """Setup for the tests
        """
        self.app = flask.Flask(__name__)
        self.app.testing = True
        self.app.secret_key = "TEST"
        models.engine = create_engine("sqlite:///:memory:")
        models.Session = sessionmaker(models.engine)
        models.session = models.Session()
        models.Base.metadata.create_all(models.engine)

    def test_own_guilds(self):
        """Test the own_guilds function
        Return all the owned guilds by the user and all the owned guild
        existing into database
        """
        server = models.Server(
            server_id="0",
            server_name="test",
            admin_id="0"
        )
        models.session.add(server)
        models.session.commit()
        user_guilds = [{'guild_id': 0, 'owner': True},
                       {'guild_id': 1, 'owner': False}]
        with self.app.test_request_context('/'):
            flask.session['user_id'] = "0"
            owned_guilds, bot_owned_guilds = discord_funcs.own_guilds(
                user_guilds)
        self.assertEqual(owned_guilds[0]['guild_id'], 0)
        self.assertEqual(bot_owned_guilds[0].server_id, "0")
        self.assertNotIn(user_guilds[1], owned_guilds)

    @mock.patch('requests_oauthlib.OAuth2Session.authorization_url',
                side_effect=mock_oauth_authorization_url)
    def test_get_login_url_discord(self, oauth_authorization_url):
        """Test the get_login_url_discord function
        """
        with self.app.test_request_context('/discord'):
            url = discord_funcs.get_login_url_discord()
            self.assertEqual('discord.login.url', url)
            self.assertEqual(flask.session['state'], "000")

    @mock.patch('requests_oauthlib.OAuth2Session.get',
                side_effect=mock_oauth2_get)
    @mock.patch('utils.discord_functions.user_infos',
                side_effect=mock_user_infos)
    def test_new_discord_user(self, oauth2_get, user_infos):
        """Test the new_discord_user function
        This function is used to put data into database and to make the link
        between user_guilds and Server stored in database
        """
        server = models.Server(
            server_id="0",
            server_name="test",
        )
        server2 = models.Server(
            server_id="1",
            server_name="test2",
        )
        models.session.add(server, server2)
        models.session.commit()
        with self.app.test_request_context('/discord'):
            flask.session['discord_token'] = "0"
            discord_funcs.new_discord_user()
            user = models.session.query(models.User).filter(
                models.User.discord_user_id == "0").first()
            self.assertEqual(user.discord_guild_ids[0].server_name, "test")
            self.assertEqual(server.discord_admin_id, "0")
            self.assertEqual(server2.discord_admin_id, None)
