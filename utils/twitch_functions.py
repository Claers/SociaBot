import json
import random

from requests_oauthlib import OAuth2Session
from flask import request, session, redirect
import requests
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
import urllib.parse as parser

import cogs.utils.settings as settings
import cogs.utils.models as models

twitch_client_id = settings.twitch_client_id
twitch_client_secret = settings.twitch_client_secret

twitch_authorize_url = "https://id.twitch.tv/oauth2/authorize"
twitch_token_url = "https://id.twitch.tv/oauth2/token"
twitch_scope = ['channel_feed_read', 'user:edit',
                'user:read:broadcast', 'user:read:email']


def get_twitch_login_url():
    """
    Get twitch login url for twitch authentification
    API ref : https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/
    DEPRECATED IN PRODUCTION DON'T WORK WITH WORKFLOW
    """
    # create an object of OAuth2Session
    oauth = OAuth2Session(
        client_id=twitch_client_id,
        redirect_uri=request.host_url + "oauth_callback_twitch",
        scope=twitch_scope
    )
    # get the login url
    login_url, state = oauth.authorization_url(twitch_authorize_url)
    session['state'] = state
    return login_url


UNICODE_ASCII_CHARACTER_SET = ('abcdefghijklmnopqrstuvwxyz'
                               'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                               '0123456789')


def generate_token(length=30, chars=UNICODE_ASCII_CHARACTER_SET):
    """Generates a non-guessable OAuth token

    OAuth (1 and 2) does not specify the format of tokens except that they
    should be strings of random characters. Tokens should not be guessable
    and entropy when generating the random characters is important. Which is
    why SystemRandom is used instead of the default random.choice method.
    """
    rand = random.SystemRandom()
    return ''.join(rand.choice(chars) for x in range(length))


def get_twitch_login_url_handmade():
    state = generate_token()
    session['state'] = state
    login_url_req = {
        "response_type": "code",
        "client_id": twitch_client_id,
        "redirect_uri": request.host_url + 'sociabot/' +
        "oauth_callback_twitch",
        "scope": twitch_scope,
        "state": session['state']
    }
    url = twitch_authorize_url + "?%s" % parser.urlencode(login_url_req, True)
    return url


def get_twitch_token_handmade():
    code = request.args.get('code')
    fetch_token_req = {
        "code": code,
        "client_id": twitch_client_id,
        "redirect_uri": request.host_url + "sociabot/" +
        "oauth_callback_twitch",
        "grant_type": "authorization_code",
        "client_secret": twitch_client_secret,
        "state": session['state']
    }
    r = requests.post(
        twitch_token_url + "?%s" % parser.urlencode(fetch_token_req, True))
    return {"access_token": r.json()['access_token'],
            "refresh_token": r.json()['refresh_token']}


def twitch_stream_set_webhook(user_id, mode):
    url = 'https://api.twitch.tv/helix/webhooks/hub'
    payload = {
        "hub.mode": mode,
        "hub.topic": "https://api.twitch.tv/helix/streams?user_id=" + user_id,
        "hub.lease_seconds": 864000,
        "hub.callback":  request.host_url +
        "sociabot/stream_webhook",
    }
    headers = {"Client-ID": twitch_client_id}
    response = requests.post(url, payload, headers=headers)
    return response.content


def get_twitch_infos(twitch):
    """
    Get twitch user infos
    API ref : https://dev.twitch.tv/docs/api/reference/#get-users
    """
    twitch_login_url = get_twitch_login_url()
    try:
        twitch_user_info = json.loads(twitch.get(
            "https://api.twitch.tv/helix/users").text)['data'][0]
        return twitch_user_info
    except (KeyError, TokenExpiredError):
        return redirect(twitch_login_url)


def add_twitch_account(existing_user, twitch):
    """Add twitch data into DataBase

    Arguments:
        existing_user {User} -- The user to link account with
        twitch {OAuth2Session} -- The twitch account credidentials
    """
    twitch_user_info = get_twitch_infos(twitch)
    twitch_account = models.TwitchAccount(
        user_id=existing_user.id,
        twitch_name=twitch_user_info['display_name'],
        twitch_id=twitch_user_info['id'],
        access_token=session['twitch_token']['access_token'],
        refresh_token=session['twitch_token']['refresh_token']
    )
    models.session.add(twitch_account)
    models.session.flush()
    existing_user.twitch_account_id = twitch_account.id
    guilds = models.session.query(models.Server).filter(
        models.Server.admin_id == existing_user.id
    ).all()
    for guild in guilds:
        guild.twitch_account_linked = twitch_account.id
    models.session.flush()
    models.session.commit()
