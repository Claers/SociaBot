import json

from requests_oauthlib import OAuth2Session
from flask import request, session, redirect
import requests
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError

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


def twitch_callback(user_id):
    url = 'https://api.twitch.tv/helix/webhooks/hub'
    print(request.host_url +
          "oauth_callback_twitch")
    payload = {
        "hub.mode": "subscribe",
        "hub.topic": "https://api.twitch.tv/helix/streams?user_id=" + user_id,
        "hub.lease_seconds": 864000,
        "hub.callback":  request.host_url +
        "oauth_callback_twitch",
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
