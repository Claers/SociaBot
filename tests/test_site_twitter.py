"""Tests for the utils.twitter_functions.py functions
"""
import requests_oauthlib
import unittest.mock as mock
import flask

from unittest import TestCase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from requests.models import Response

import utils.twitter_functions as twitter_funcs
import cogs.utils.models as models


def mock_resource_token_get(url):
    """Mock the OAuth1Session.get() function
    Return Response object with text
    """
    resp = Response()
    resp.status_code = 200
    type(resp).text = mock.PropertyMock(
        return_value="oauth_token=token_test&oauth_token_secret=secret_test"
    )
    return resp


def mock_access_token_post(url, data):
    """Mock the OAuth1Session.post() function
    Return Response object with text
    """
    resp = Response()
    resp.status_code = 200
    type(resp).text = mock.PropertyMock(
        return_value="oauth_token=token_test&oauth_token_secret=secret_test&" +
        "user_id=0&screen_name=test_name"
    )
    return resp


class TestTwitterUtilsFunctions(TestCase):
    """Tests for the twitter functions contained in utils/twitter_function.py
    These functions are used in the website for the twitter part
    """

    def setUp(self):
        """Setup for the tests
        """
        self.app = flask.Flask(__name__)
        self.app.testing = True
        models.engine = create_engine("sqlite:///:memory:")
        models.Session = sessionmaker(models.engine)
        models.session = models.Session()
        models.Base.metadata.create_all(models.engine)

    @mock.patch('requests_oauthlib.OAuth1Session.get',
                side_effect=mock_resource_token_get)
    def test_twitter_get_resource_token(self, resource_token_get):
        """Test the twitter_get_resource_token function
        Test the splitting of response text
        """
        with self.app.test_request_context('/twitter'):
            resource = twitter_funcs.twitter_get_resource_token()
            self.assertEqual(resource, ["token_test", "secret_test"])

    @mock.patch('requests_oauthlib.OAuth1Session.post',
                side_effect=mock_access_token_post)
    def test_twitter_get_access_token(self, access_token_post):
        """Test the twitter_get_access_token function
        Test the splitting of response text
        """
        with self.app.test_request_context('/twitter'):
            data = twitter_funcs.twitter_get_access_token(
                "test", "test", "test")
            self.assertEqual(
                data, ("token_test", "secret_test", "0", "test_name")
            )
