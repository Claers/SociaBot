from requests_oauthlib import OAuth1Session
from flask import request, url_for
import cogs.utils.settings as settings
import cogs.utils.models as models


twitter_consumer_key = settings.twitter_key
twitter_consumer_secret = settings.twitter_secret


def twitter_get_resource_token():
    """
    Get the resource token for twitter authentification
    API ref : https://developer.twitter.com/en/docs/basics/authentication/
    api-reference/request_token
    Resource token should be used with this url to connect user :
    https://api.twitter.com/oauth/authenticate?oauth_token={{ro_key}}
    """
    # create an object of OAuth1Session
    request_token = OAuth1Session(
        client_key=twitter_consumer_key,
        client_secret=twitter_consumer_secret,
        callback_uri=request.host_url[:-1] + url_for('oauth_callback_twitter')
    )
    # twitter endpoint to get request token
    url = 'https://api.twitter.com/oauth/request_token'
    # get request_token_key, request_token_secret and other details
    data = request_token.get(url)
    print(data.text)
    # split the string to get relevant data
    data_token = str.split(data.text, '&')
    ro_key = str.split(data_token[0], '=')
    ro_secret = str.split(data_token[1], '=')
    resource_owner_key = ro_key[1]
    resource_owner_secret = ro_secret[1]
    resource = [resource_owner_key, resource_owner_secret]
    return resource


def twitter_get_access_token(verifier, ro_key, ro_secret):
    """
    Get the access token for twitter
    API ref : https://developer.twitter.com/en/docs/basics/authentication/
    api-reference/access_token
    Access token are used to communicate with the twitter account of the user
    """
    # create an object of OAuth1Session
    oauth_token = OAuth1Session(client_key=twitter_consumer_key,
                                client_secret=twitter_consumer_secret,
                                resource_owner_key=ro_key,
                                resource_owner_secret=ro_secret)
    # twitter endpoint to get access token
    url = 'https://api.twitter.com/oauth/access_token'
    data = {"oauth_verifier": verifier}
    # get request_access_token, request_access_secret and other data
    access_token_data = oauth_token.post(url, data=data)
    access_token_list = str.split(access_token_data.text, '&')
    # split the string to get revelant data
    if len(access_token_list) > 1:
        token = str.split(access_token_list[0], '=')[1]
        secret = str.split(access_token_list[1], '=')[1]
        user_id = str.split(access_token_list[2], '=')[1]
        username = str.split(access_token_list[3], '=')[1]
        return token, secret, user_id, username
    else:
        return "Error"


def add_twitter_account(existing_user, username, token, secret, user_id):
    """Add twitter data to DataBase
    """
    twitter_account = models.TwitterAccount(
        user_id=existing_user.id,
        twitter_name=username,
        access_token=token,
        access_secret=secret,
        account_user_id=user_id
    )
    models.session.add(twitter_account)
    models.session.flush()
    models.session.commit()
