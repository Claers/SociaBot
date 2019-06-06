"""Tests for the utils.twitch_functions.py functions
"""
import requests_oauthlib
import unittest.mock as mock
import flask
import json

from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from requests.models import Response

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
    resp = Response()
    resp.status_code = 200
    data = json.dumps({
        'data': [{'username': 'test'}]
    })
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
        """Test the get_twitch_infos function
        """
        with self.app.test_request_context('/twitch'):
            infos = twitch_funcs.get_twitch_infos(
                requests_oauthlib.OAuth2Session)
            self.assertEqual('test', infos['username'])
