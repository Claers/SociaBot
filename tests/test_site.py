import requests_oauthlib
import json

import unittest.mock as mock
from flask import Flask, session
from unittest import TestCase
from requests.models import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import website
import utils.discord_functions
import cogs.utils.models as models


def mock_oauth2_get(url):
    if 'avatar' in url:
        resp = Response()
        resp.status_code = 200
        type(resp).url = mock.PropertyMock(
            return_value="avatar.com"
        )
        return resp


def mock_user_infos(discord_auth):
    return {'id': '0', 'username': 'testUser', 'avatar': '0'}


def mock_discord_func_user_info(discord):
    return {"id": "0"}


class MockOAuth2Session(requests_oauthlib.OAuth2Session):
    def __init__(self):
        pass

    def get(self, url):
        resp = Response()
        resp.status_code = 200
        data = '[{"id": "0", "owner": "True"}, {"id": "1", "owner": "False"}]'
        type(resp).text = mock.PropertyMock(
            return_value=data
        )
        return resp


class TestSite(TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.app.secret_key = "TEST"
        self.test_client = website.app.test_client()
        models.engine = create_engine("sqlite:///:memory:")
        models.Session = sessionmaker(models.engine)
        models.session = models.Session()
        models.Base.metadata.create_all(models.engine)
        twitter_account = models.TwitterAccount(
            twitter_name="test_twitter"
        )
        models.session.add(twitter_account)
        twitch_account = models.TwitchAccount(
            twitch_name="test_twitch"
        )
        models.session.add(twitch_account)
        models.session.flush()
        user = models.User(
            discord_user_id="0",
            dark_theme_enabled=True,
            twitter_account_id=twitter_account.id,
            twitch_account_id=twitch_account.id
        )
        models.session.add(user)
        models.session.flush()
        twitter_account.user_id = user.id
        twitch_account.user_id = user.id
        server = models.Server(
            server_id="0",
            server_name="test_server"
        )
        models.session.add(server)
        models.session.flush()
        models.session.commit()

    def test_index_not_logged(self):
        """Test if the login_required decorator works
        """
        response = self.test_client.get("/sociabot/")
        self.assertTrue(response.status_code == 302)

    @mock.patch('requests_oauthlib.OAuth2Session.get',
                side_effect=mock_oauth2_get)
    @mock.patch('utils.discord_functions.user_infos',
                side_effect=mock_user_infos)
    def test_index_logged(self, oauth2_get, user_infos):
        """Test if the login_required decorator works and the home page
        """
        with self.test_client.session_transaction() as sess:
            sess['discord_token'] = "0"
            sess['black_theme'] = True
        response = self.test_client.get("/sociabot/")
        # test if request is done successfully
        self.assertTrue(response.status_code == 200)
        # test if username is passed successfully from user_infos
        self.assertTrue('testUser' in str(response.data))
        # test if avatar url is passed sucessfully from oauth2_get
        self.assertTrue('avatar.com' in str(response.data))

    @mock.patch('utils.discord_functions.user_infos',
                side_effect=mock_discord_func_user_info)
    def test_get_user(self, discord_func_user_info):
        """Test the website.get_user function
        Send user data from DataBase to session parameters
        """
        with self.app.test_request_context('/'):
            website.get_user(MockOAuth2Session())
            server = models.session.query(models.Server).filter(
                models.Server.server_id == "0"
            ).first()
            self.assertEqual(server.admin_id, 1)
            self.assertEqual(session['twitter_accounts'][0][2], "test_twitter")
            self.assertEqual(session['twitch_accounts'][0][2], "test_twitch")
