"""Tests for the utils.twitch_functions.py functions
"""
import requests_oauthlib
import unittest.mock as mock
import json

import flask
from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import requests


import utils.twitch_functions as twitch_funcs
import cogs.utils.models as models


def mock_oauth_authorization_url(url):
    """Mock the OAuth2Session.authorization_url
    Return url and state for testing
    """
    return "twitch.login.url", "000"


def mock_oauth2_get(url):
    """Mock the OAuth2Session.get
    Return Response with json data
    """
    resp = requests.models.Response()
    resp.status_code = 200
    data = '{"data": [{"username": "test"}]}'
    type(resp).text = mock.PropertyMock(
        return_value=data
    )
    return resp


def mock_requests_post(url):
    resp = requests.models.Response()
    resp.status_code = 200
    data = '{"access_token": "test_token", "refresh_token": "test_refresh"}'
    type(resp).text = mock.PropertyMock(
        return_value=data
    )
    return resp


class TestTwitchUtilsFunctions(TestCase):
    """Tests for the twitter functions contained in utils/twitch_functions.py
    These functions are used in the website for the twitch part
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

    @mock.patch('requests_oauthlib.OAuth2Session.authorization_url',
                side_effect=mock_oauth_authorization_url)
    def test_get_twitch_login_url(self, oauth_authorization_url):
        """Test the get_twitch_login_url function
        DEPRECATED IN PRODUCTION DON'T WORK WITH WORKFLOW
        """
        with self.app.test_request_context('/twitch'):
            url = twitch_funcs.get_twitch_login_url()
            self.assertEqual('twitch.login.url', url)
            self.assertEqual(flask.session['state'], "000")

    @mock.patch('requests_oauthlib.OAuth2Session.get',
                side_effect=mock_oauth2_get)
    @mock.patch('requests_oauthlib.OAuth2Session.authorization_url',
                side_effect=mock_oauth_authorization_url)
    def test_get_twitch_infos(self, oauth2_get_json, oauth_authorization_url):
        """Test the utils.twitch_functions.get_twitch_infos function
        Get twitch user infos
        """
        with self.app.test_request_context('/twitch'):
            infos = twitch_funcs.get_twitch_infos(
                requests_oauthlib.OAuth2Session)
            self.assertEqual('test', infos['username'])

    def test_get_twitch_login_url_handmade(self):
        """Test the utils.twitch_functions.get_twitch_login_url_handmade func
        This function prepare the twitch url for login
        """
        with self.app.test_request_context('/twitch'):
            url = twitch_funcs.get_twitch_login_url_handmade()
            self.assertIn(
                "https://id.twitch.tv/oauth2/authorize?response_type=code" +
                "&client_id=3qlv5zeohxvs9rqd58q48n7m97ejoc&redirect_uri=" +
                "http%3A%2F%2Flocalhost%2Fsociabot%2Foauth_callback_twitch" +
                "&scope=channel_feed_read&scope=user%3Aedit" +
                "&scope=user%3Aread%3Abroadcast" +
                "&scope=user%3Aread%3Aemail&state=", url)

    @mock.patch('requests.post',
                side_effect=mock_requests_post)
    def test_get_twitch_token_handmade(self, request_post):
        """Test the utils.twitch_functions.get_twitch_token_handmade func
        This function get the twitch tokens
        """
        with self.app.test_request_context(
                '/sociabot/oauth_callback_twitch?code=test'):
            flask.session['state'] = "test"
            tokens = twitch_funcs.get_twitch_token_handmade()
            self.assertEqual("test_token", tokens['access_token'])
            self.assertEqual("test_refresh", tokens['refresh_token'])
