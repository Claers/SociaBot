import cogs.utils.settings as settings
import cogs.utils.models as models
import cogs.utils.languages as lang
from flask import Flask
from flask import session, request, url_for
from flask import redirect, render_template
from requests_oauthlib import OAuth1Session, OAuth2Session
from oauthlib.oauth2.rfc6749.errors import TokenExpiredError
from functools import wraps
import requests
import os
from urllib.parse import quote_plus, unquote

template_dir = os.path.abspath('./site/templates')
static_dir = os.path.abspath('./site/static')
app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir
)


# Settings for your app
app.debug = True
app.secret_key = 'development'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
base_discord_api_url = 'https://discordapp.com/api'
discord_cdn = "https://cdn.discordapp.com/"
scope = ['identify', 'email', 'connections', 'guilds']
token_url = 'https://discordapp.com/api/oauth2/token'
authorize_url = 'https://discordapp.com/api/oauth2/authorize'
twitch_authorize_url = "https://id.twitch.tv/oauth2/authorize"
twitch_token_url = "https://id.twitch.tv/oauth2/token"
twitch_scope = ['channel_feed_read', 'user:edit',
                'user:read:broadcast', 'user:read:email']
# Keys and secrets
client_id = settings.discord_client_id
client_secret = settings.discord_client_secret
twitch_client_id = settings.twitch_client_id
twitch_client_secret = settings.twitch_client_secret
twitter_consumer_key = settings.twitter_key
twitter_consumer_secret = settings.twitter_secret


def login_required(f):
    """
    Decorator that verify if the user is logged with discord
    """
    @wraps(f)
    def decorated_funtion(*args, **kwargs):
        if session.get('discord_token') is None:
            return redirect(url_for('discord_connection', next=request.url))
        return f(*args, **kwargs)
    return decorated_funtion


def own_guilds(user_guilds):
    """
    Funtion used to return in two separate list the guilds owned by the
    user not registered into database from guilds registered

    Arguments:
        user_guilds {json} -- All guilds from user

    Returns:
        owned_guilds {list} -- The user owned guilds by the user without
                                    registered one into the database
        bot_owned_guilds {list} -- The user owned guilds registered
                                    into the database
    """
    owned_guilds = []
    bot_owned_guilds = []
    bot_owned_guilds = models.session.query(models.Server).filter(
        models.Server.admin_id == str(session['user_id'])
    ).all()
    for user_guild in user_guilds:
        if user_guild['owner'] is True:
            owned_guilds.append(user_guild)
    return owned_guilds, bot_owned_guilds


def get_login_url_discord():
    """
    Get the login url for discord authentification
    The request is CSRF securized with a state stored in session
    API ref: https://discordapp.com/developers/docs/topics/oauth2
    Authorization Url : https://discordapp.com/api/oauth2/authorize
    """
    # create an object of Oauth2Session
    oauth = OAuth2Session(
        client_id=client_id,
        redirect_uri=request.host_url + "oauth_callback_discord",
        scope=scope
    )
    # get the login url and the state
    login_url, state = oauth.authorization_url(authorize_url)
    # store the state in session to be able to reuse in next step
    session['state'] = state
    return login_url


def user_infos(discord_auth):
    """Get the discord user infos
    API ref: https://discordapp.com/developers/docs/resources/user#get-user
    Endpoint : /users/@me
    Arguments:
        discord_auth {Oauth2Session} -- The discord oauth session used to make
                                        the requests
    """
    user_infos = discord_auth.get(
        base_discord_api_url + '/users/@me').json()
    return user_infos


def new_discord_user():
    """
    Create a user object to be send to DataBase
    Use discord user informations
    """
    # if user is not authenticated go to authentification view
    if session.get('discord_token') is None:
        return redirect(url_for('discord_view'))
    # create object of Oauth2Session
    discord = OAuth2Session(client_id, token=session['discord_token'])
    discord_user_infos = user_infos(discord)
    # create object of User
    user = models.User(
        discord_user_id=discord_user_infos['id'],
        dark_theme_enabled=True
    )
    models.session.add(user)
    models.session.flush()
    discord_guilds = []
    # get user connected "guilds" (discord server)
    user_guilds = discord.get(
        base_discord_api_url + '/users/@me/guilds').json()
    # set user owned guild if guild is in DataBase
    for user_guild in user_guilds:
        guild = models.session.query(models.Server).filter(
            models.Server.server_id == user_guild['id']).first()
        if guild is not None:
            discord_guilds.append(guild)
            guild.users_id.append(user)
            if(user_guild['owner']):
                guild.admin_id = user.id
    # set user connected guild in DataBase
    for discord_guild in discord_guilds:
        user.discord_guild_ids.append(discord_guild)
    models.session.flush()
    models.session.commit()
    # create data into the session
    get_discord_user(discord)


def get_discord_user(discord):
    """
    Send user data from DataBase to session parameters

    Arguments:
        discord {Oauth2Session} -- The discord oauth session used to make
                                        the requests
    """
    # get user id
    user_id = user_infos(discord)['id']
    # get user object from DataBase
    existing_user = models.session.query(models.User).filter(
        models.User.discord_user_id == user_id).first()
    twitter_accounts = models.session.query(models.TwitterAccount).filter(
        models.TwitterAccount.user_id == existing_user.id
    ).all()
    # store user infos into session
    session['user_id'] = existing_user.id
    session['black_theme'] = existing_user.dark_theme_enabled
    if twitter_accounts is not None:
        twitter_accounts_cred = []
        for twitter_account in twitter_accounts:
            creditentials = []
            creditentials.append(twitter_account.access_token)
            creditentials.append(twitter_account.access_secret)
            creditentials.append(twitter_account.twitter_name)
            creditentials.append(twitter_account.id)
            twitter_accounts_cred.append(creditentials)
        session['twitter_accounts'] = twitter_accounts_cred
    if existing_user.twitch_account_id is not None:
        twitch_account = []
        creditentials = []
        creditentials.append(twitch_account.twitch_access_token)
        creditentials.append(twitch_account.twitchaccess_secret)
        creditentials.append(twitch_account.twitch_name)
        creditentials.append(twitch_account.id)
        twitch_account.append(creditentials)
        session['twitch_accounts'] = twitch_account


@app.route('/discord')
def discord_connection():
    """
    Return to discord login url
    """
    login_url = get_login_url_discord()
    return redirect(login_url)


@app.route("/oauth_callback_discord")
def oauth_callback_discord():
    """
    The callback we specified in our app.
    Processes the code given to us by Discord and sends it back
    to Discord requesting a temporary access token so we can
    make requests on behalf (as if we were) the user.
    The token is stored in a session variable, so it can
    be reused across separate web requests.
    """
    # create an object of Oauth2Session
    discord = OAuth2Session(
        client_id=client_id,
        redirect_uri=request.host_url + "oauth_callback_discord",
        state=session['state'],
        scope=scope
    )
    # get discord token
    token = discord.fetch_token(
        token_url,
        client_secret=client_secret,
        authorization_response=request.url,
    )
    # store token in session
    session['discord_token'] = token
    user_id = user_infos(discord)['id']
    # fetch for an corresponding user in database
    existing_user = models.session.query(models.User).filter(
        models.User.discord_user_id == user_id).first()
    if existing_user is None:
        new_discord_user()
    else:
        get_discord_user(discord)
    return redirect(url_for('index'))


@app.route('/')
@login_required
def index():
    discord = OAuth2Session(client_id, token=session.get('discord_token'))
    user_info = user_infos(discord)
    avatar = discord.get(discord_cdn + 'avatars/' +
                         user_info['id'] + '/' + user_info['avatar'] + '.png')
    return render_template(
        "index.html",
        black_theme=session['black_theme'],
        avatar_url=avatar.url,
        username=user_info['username'])


def twitter_get_resource_token():
    """
    Get the resource token for twitter authentification
    API ref : https://developer.twitter.com/en/docs/basics/authentication/
    api-reference/request_token
    Resource token should be used with this url to connect user :
    https://api.twitter.com/oauth/authenticate?oauth_token={{resource_owner_key}}
    """
    # create an object of OAuth1Session
    request_token = OAuth1Session(
        client_key=twitter_consumer_key,
        client_secret=twitter_consumer_secret,
        callback_uri=request.host_url + "oauth_callback_twitter"
    )
    # twitter endpoint to get request token
    url = 'https://api.twitter.com/oauth/request_token'
    # get request_token_key, request_token_secret and other details
    data = request_token.get(url)
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


@app.route('/twitter')
@login_required
def twitter():
    discord = OAuth2Session(client_id, token=session['discord_token'])
    user_info = user_infos(discord)
    get_discord_user(discord)
    resource = twitter_get_resource_token()
    session['ro_key'] = resource[0]
    session['ro_secret'] = resource[1]
    avatar = discord.get(discord_cdn + 'avatars/' +
                         user_info['id'] + '/' + user_info['avatar'] + '.png')
    twitter_accounts = models.session.query(models.TwitterAccount).filter(
        models.TwitterAccount.user_id == session['user_id']
    ).all()
    print(twitter_accounts[0]._json())
    bot_user_guilds = models.session.query(models.Server).filter(
        models.Server.users_id.any(models.User.id == str(session['user_id']))).all()
    if session.get("twitter_account_added") is not None:
        confirm_tw_added = True
        session.pop("twitter_account_added")
    else:
        confirm_tw_added = False
    if session.get("twitter_account_exist") is not None:
        tw_already_exist = True
        session.pop("twitter_account_exist")
    else:
        tw_already_exist = False
    return render_template(
        "twitter.html",
        ro_key=resource[0],
        black_theme=session['black_theme'],
        avatar_url=avatar.url,
        username=user_info['username'],
        twitter_accounts=twitter_accounts,
        bot_user_guilds=bot_user_guilds,
        confirm_tw_added=confirm_tw_added,
        tw_already_exist=tw_already_exist
    )


@app.route('/oauth_callback_twitter')
@login_required
def oauth_callback_twitter():
    ro_key = session['ro_key']
    ro_secret = session['ro_secret']
    verifier = request.args.get('oauth_verifier')
    token, secret, user_id, username = twitter_get_access_token(
        verifier, ro_key, ro_secret)
    discord = OAuth2Session(client_id, token=session['discord_token'])
    db_user_id = str(session['user_id'])
    existing_user = models.session.query(models.User).filter(
        models.User.id == db_user_id).first()
    account = models.session.query(models.TwitterAccount).filter(
        models.TwitterAccount.account_user_id == user_id
    ).first()
    if account is None:
        add_twitter_account(existing_user, username, token, secret, user_id)
        session['twitter_account_added'] = True
    else:
        session['twitter_account_exist'] = True
    get_discord_user(discord)

    return(redirect(url_for('twitter')))


@app.route('/twitter_update_infos/')
@login_required
def twitter_update_infos():
    data = request.get_json()
    twitter_accounts = models.session.query(models.TwitterAccount).filter(
        models.TwitterAccount.user_id == str(session['user_id'])
    ).all()
    for twitter_account in twitter_accounts:
        print(data[twitter_account.account_user_id])
    return redirect(url_for('twitter'))


def get_twitch_token():
    oauth = OAuth2Session(
        client_id=twitch_client_id,
        redirect_uri=request.host_url + "oauth_callback_twitch",
        scope=twitch_scope
    )
    login_url, state = oauth.authorization_url(twitch_authorize_url)
    session['state'] = state
    return login_url


def twitch_callback(user_id):
    url = 'https://api.twitch.tv/helix/webhooks/hub'
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
    twitch_login_url = get_twitch_token()
    try:
        twitch_user_info = twitch.get(
            "https://api.twitch.tv/helix/users").json()['data'][0]
        return twitch_user_info
    except (KeyError, TokenExpiredError):
        return redirect(twitch_login_url)


def add_twitch_account(existing_user, twitch):
    twitch_user_info = get_twitch_infos(twitch)
    twitch_account = models.TwitchAccount(
        twitch_name=twitch_user_info['display_name'],
        twitch_id=twitch_user_info['id'],
        twitch_access_token=session['twitch_token']['access_token'],
        twitch_refresh_token=session['twitch_token']['refresh_token']
    )
    models.session.add(twitch_account)
    models.session.flush()
    existing_user.twitch_account_id.append(twitch_account)
    models.session.flush()
    models.session.commit()


@app.route('/twitch')
@login_required
def twitch():
    twitch_login_url = url_for("connect_twitch")
    if session.get('twitch_token') is not None:
        twitch = OAuth2Session(
            twitch_client_id, token=session['twitch_token'])
        twitch_user_info = get_twitch_infos(twitch)
        if type(twitch_user_info) == dict:
            discord = OAuth2Session(client_id, token=session['discord_token'])
            user_info = user_infos(discord)
            avatar = discord.get(discord_cdn + 'avatars/' +
                                 user_info['id'] + '/' + user_info['avatar']
                                 + '.png')
            user_guilds = discord.get(
                base_discord_api_url + '/users/@me/guilds').json()
            owned_guilds, bot_owned_guilds = own_guilds(user_guilds)
            twitch_account = models.session.query(models.TwitchAccount).filter(
                models.TwitchAccount.twitch_id == twitch_user_info['id']
            ).first()
            print(twitch_account.notification_activated_on)
            return render_template(
                "twitch.html",
                black_theme=session['black_theme'],
                twitch_login_url=twitch_login_url,
                twitch_accounts=twitch_user_info,
                owned_guilds=bot_owned_guilds,
                avatar_url=avatar.url,
                twitch_account=twitch_account
            )
        else:
            return twitch_user_info
    else:
        return redirect(twitch_login_url)


@app.route('/connect_twitch')
@login_required
def connect_twitch():
    return redirect(get_twitch_token())


@app.route('/oauth_callback_twitch')
@login_required
def oauth_callback_twitch():
    twitch = OAuth2Session(
        client_id=twitch_client_id,
        redirect_uri=request.host_url + "oauth_callback_twitch",
        state=session['state'],
        scope=twitch_scope
    )
    token = twitch.fetch_token(
        twitch_token_url,
        client_secret=twitch_client_secret,
        authorization_response=request.url,
    )
    session['twitch_token'] = token
    user_id = str(session['user_id'])
    twitch_user_info = get_twitch_infos(twitch)
    existing_user = models.session.query(models.User).filter(
        models.User.id == user_id).first()
    account = models.session.query(models.TwitchAccount).filter(
        models.TwitchAccount.twitch_id == twitch_user_info['id']
    ).first()
    if account is None:
        add_twitch_account(existing_user, twitch)
        session['twitch_account_added'] = True
    else:
        account.twitch_access_token = session[
            'twitch_token']['access_token']
        account.twitch_refresh_token = session[
            'twitch_token']['refresh_token']
        models.session.flush()
        models.session.commit()
        session['twitch_account_exist'] = True
    return redirect(url_for('twitch'))


@app.route('/twitch_notif/<server>')
@login_required
def twitch_notif(server):
    print(session[
        'twitch_token']['access_token'])
    twitch_account = models.session.query(models.TwitchAccount).filter(
        models.TwitchAccount.twitch_access_token == session[
            'twitch_token']['access_token']
    ).first()
    server_obj = models.session.query(models.Server).filter(
        models.Server.id == server
    ).first()
    if server_obj in twitch_account.notification_activated_on:
        twitch_account.notification_activated_on.remove(server_obj)
        models.session.flush()
        models.session.commit()
    else:
        twitch_account.notification_activated_on.append(server_obj)
        models.session.flush()
        models.session.commit()
    return redirect(url_for('twitch'))


@app.route("/profile")
@login_required
def profile():
    """
    User profile page
    Used to Invite/Exclude bot from server
    Used to see user personnal informations.
    """
    discord = OAuth2Session(client_id, token=session['discord_token'])
    user_info = user_infos(discord)
    avatar = discord.get(discord_cdn + 'avatars/' +
                         user_info['id'] + '/' + user_info['avatar'] + '.png')
    user_guilds = discord.get(
        base_discord_api_url + '/users/@me/guilds').json()
    owned_guilds, bot_owned_guilds = own_guilds(user_guilds)
    if session.get("bot_server_added") is not None:
        confirm_bot_added = True
        session.pop("bot_server_added")
    else:
        confirm_bot_added = False
    return render_template(
        "profile.html",
        black_theme=session['black_theme'],
        avatar_url=avatar.url,
        username=user_info['username'],
        owned_guilds=owned_guilds,
        bot_owned_guilds=bot_owned_guilds,
        confirm_bot_added=confirm_bot_added
    )


@app.route("/bot-server-added")
@login_required
def bot_server_added():
    session['bot_server_added'] = True
    return redirect(url_for('profile'))


@app.route("/invite_to/<server_name>")
@login_required
def invite_bot_to(server_name):
    server_name = unquote(server_name)
    print(server_name)
    return redirect(url_for('index'))


@app.route('/blacktheme/<enabled>/<actualUrl>')
@login_required
def black_theme(enabled, actualUrl):
    user = models.session.query(models.User).filter(
        models.User.id == str(session['user_id'])).first()
    if(enabled == "True"):
        session['black_theme'] = False
        user.dark_theme_enabled = False
    else:
        session['black_theme'] = True
        user.dark_theme_enabled = True
    models.session.flush()
    models.session.commit()
    return redirect(unquote(actualUrl))


@app.context_processor
def utility_processor():
    return dict(quote_plus=quote_plus, str=str)


if __name__ == '__main__':
    app.run()
