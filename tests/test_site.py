import requests_oauthlib
import unittest.mock as mock

from flask import Flask, session
from unittest import TestCase
from requests.models import Response

from website import app
import utils.discord_functions


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


class TestSite(TestCase):

    def setUp(self):
        app.testing = True
        self.app = app.test_client()

    def test_index_not_logged(self):
        """Test if the login_required decorator works
        """
        response = self.app.get("/")
        self.assertTrue(response.status_code == 302)

    @mock.patch('requests_oauthlib.OAuth2Session.get',
                side_effect=mock_oauth2_get)
    @mock.patch('utils.discord_functions.user_infos',
                side_effect=mock_user_infos)
    def test_index_logged(self, oauth2_get, user_infos):
        """The if the login_required decorator works and the home page
        """
        with self.app.session_transaction() as sess:
            sess['discord_token'] = "0"
            sess['black_theme'] = True
        response = self.app.get("/")
        # test if request is done successfully
        self.assertTrue(response.status_code == 200)
        # test if username is passed successfully from user_infos
        self.assertTrue('testUser' in str(response.data))
        # test if avatar url is passed sucessfully from oauth2_get
        self.assertTrue('avatar.com' in str(response.data))

    def test_get_user(self):
        pass
