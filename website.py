"""This website is used to configurate SociaBot for user
"""
import json
import os
from functools import wraps

import oauthlib
from flask import Flask
from flask import session, request, url_for
from flask import redirect, render_template
from requests_oauthlib import OAuth2Session
from urllib.parse import quote_plus, unquote

import utils.twitter_functions as twitter_func
import utils.twitch_functions as twitch_func
import utils.discord_functions as discord_func
import cogs.utils.settings as settings
import cogs.utils.models as models


dir_path = os.path.dirname(os.path.realpath(__file__))
template_dir = os.path.normpath(os.path.join(dir_path, './site/templates'))
static_dir = os.path.normpath(os.path.join(dir_path,  './site/staticSociaBot'))
app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
)


# Settings for your app
app.debug = True
secret = os.environ.get("app_secret_key")
if secret is None:
    app.secret_key = 'test'
else:
    app.secret_key = secret

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

base_discord_api_url = 'https://discordapp.com/api'
discord_cdn = "https://cdn.discordapp.com/"
token_url = 'https://discordapp.com/api/oauth2/token'
scope = ['identify', 'email', 'connections', 'guilds']


# Keys and secrets
client_id = settings.discord_client_id
client_secret = settings.discord_client_secret


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


def get_user(discord):
    """
    Send user data from DataBase to session parameters

    Arguments:
        discord {Oauth2Session} -- The discord oauth session used to make
                                        the requests
    """
    # get user id
    user_id = discord_func.user_infos(discord)['id']
    # get user object from DataBase
    existing_user = models.session.query(models.User).filter(
        models.User.discord_user_id == user_id).first()
    twitter_accounts = models.session.query(models.TwitterAccount).filter(
        models.TwitterAccount.user_id == existing_user.id
    ).all()
    twitch_account = models.session.query(models.TwitchAccount).filter(
        models.TwitchAccount.id == existing_user.twitch_account_id
    ).first()
    # store user infos into session
    session['user_id'] = existing_user.id
    session['black_theme'] = existing_user.dark_theme_enabled
    discord_guilds = []
    # get user connected "guilds" (discord server)
    user_guilds = discord.get(
        base_discord_api_url + '/users/@me/guilds').json()
    # set user owned guild if guild is in DataBase
    for user_guild in user_guilds:
        guild = models.session.query(models.Server).filter(
            models.Server.server_id == str(user_guild['id'])).first()
        if guild is not None:
            discord_guilds.append(guild)
            guild.users_id.append(existing_user)
            if(user_guild['owner']):
                guild.admin_id = existing_user.id
    # set user connected guild in DataBase
    for discord_guild in discord_guilds:
        existing_user.discord_guild_ids.append(discord_guild)
    models.session.flush()
    models.session.commit()
    # put twitter account creditentials into session
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
    # put twitch account creditentials into session
    if twitch_account is not None:
        twitch_account_cred = []
        creditentials = []
        creditentials.append(twitch_account.access_token)
        creditentials.append(twitch_account.refresh_token)
        creditentials.append(twitch_account.twitch_name)
        creditentials.append(twitch_account.id)
        twitch_account_cred.append(creditentials)
        session['twitch_accounts'] = twitch_account_cred


@app.route('/sociabot/discord')
def discord_connection():
    """
    Return to discord login url
    """
    login_url = discord_func.get_login_url_discord()
    return redirect(login_url)


@app.route('/sociabot/oauth_callback_discord')
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
        redirect_uri=request.host_url + "sociabot/" + "oauth_callback_discord",
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
    user_id = discord_func.user_infos(discord)['id']
    # fetch for an corresponding user in database
    existing_user = models.session.query(models.User).filter(
        models.User.discord_user_id == user_id).first()
    if existing_user is None:
        discord_func.new_discord_user()
        # create data into the session
        get_user(discord)
    else:
        get_user(discord)
    file = open("need_to_reload", "w")
    file.close()
    return redirect(url_for('index'))


@app.route('/sociabot/')
@login_required
def index():
    """The home page
    """
    discord = OAuth2Session(client_id, token=session.get('discord_token'))
    try:
        user_info = discord_func.user_infos(discord)
    except oauthlib.oauth2.rfc6749.errors.TokenExpiredError:
        return redirect(url_for('discord_connection'))
    avatar = discord.get(discord_cdn + 'avatars/' +
                         user_info['id'] + '/' + user_info['avatar'] + '.png')
    return render_template(
        "index.html",
        black_theme=session['black_theme'],
        avatar_url=avatar.url,
        username=user_info['username'])


@app.route('/sociabot/twitter')
@login_required
def twitter():
    """The twitter configuration page
    """
    discord = OAuth2Session(client_id, token=session['discord_token'])
    user_info = discord_func.user_infos(discord)
    get_user(discord)
    resource = twitter_func.twitter_get_resource_token()
    session['ro_key'] = resource[0]
    session['ro_secret'] = resource[1]
    avatar = discord.get(discord_cdn + 'avatars/' +
                         user_info['id'] + '/' + user_info['avatar'] + '.png')
    # get all twitter account linked to user
    twitter_accounts = models.session.query(models.TwitterAccount).filter(
        models.TwitterAccount.user_id == session['user_id']
    ).all()
    twitter_accounts_json = []
    # get twitter account json
    for twitter_account in twitter_accounts:
        twitter_accounts_json.append(twitter_account._json())
    # get all guild where user is the admin
    bot_user_guilds = models.session.query(models.Server).filter(
        models.Server.admin_id == str(session['user_id'])
    ).all()
    # get all channels for the guilds
    channels = discord_func.get_text_channels_for_user(
        bot_user_guilds)
    # get guilds json
    bot_user_guilds_json = []
    for bot_user_guild in bot_user_guilds:
        bot_user_guilds_json.append(bot_user_guild._json())
    # notification manager
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
    if session.get("twitter_account_updated") is not None:
        tw_updated = True
        session.pop("twitter_account_updated")
    else:
        tw_updated = False
    return render_template(
        "twitter.html",
        ro_key=resource[0],
        black_theme=session['black_theme'],
        avatar_url=avatar.url,
        username=user_info['username'],
        twitter_accounts=twitter_accounts_json,
        channels=channels,
        bot_user_guilds=bot_user_guilds_json,
        tw_updated=tw_updated,
        confirm_tw_added=confirm_tw_added,
        tw_already_exist=tw_already_exist,

    )


@app.route('/sociabot/oauth_callback_twitter')
@login_required
def oauth_callback_twitter():
    """Callback url for twitter authentification
    """
    ro_key = session['ro_key']
    ro_secret = session['ro_secret']
    verifier = request.args.get('oauth_verifier')
    token, secret, user_id, username = twitter_func.twitter_get_access_token(
        verifier, ro_key, ro_secret)
    discord = OAuth2Session(client_id, token=session['discord_token'])
    db_user_id = str(session['user_id'])
    existing_user = models.session.query(models.User).filter(
        models.User.id == db_user_id).first()
    account = models.session.query(models.TwitterAccount).filter(
        models.TwitterAccount.account_user_id == user_id
    ).first()
    if account is None:
        twitter_func.add_twitter_account(
            existing_user, username, token, secret, user_id)
        session['twitter_account_added'] = True
    else:
        session['twitter_account_exist'] = True
    get_user(discord)
    file = open("need_to_reload", "w")
    file.close()
    return(redirect(url_for('twitter')))


@app.route('/sociabot/twitter_update_infos/', methods=['POST'])
@login_required
def twitter_update_infos():
    """View used only in POST to get data from twitter configuration page
    """
    if request.method == 'POST':
        data = request.json
        for server_data in data:
            server = models.session.query(models.Server).filter(
                models.Server.server_id == str(server_data['server_id'])
            ).first()
            try:
                if not (server_data['twitter_account_id'] == "None" or
                        server_data['twitter_account_id'] is None):
                    server.twitter_account_linked = int(
                        server_data['twitter_account_id'])
            except KeyError:
                server.twitter_account_linked = None
            try:
                if not (server_data['notif_id'] == "None" or
                        server_data['notif_id'] is None):
                    server.notification_channel_twitter = str(
                        server_data['notif_id'])
            except KeyError:
                server.notification_channel_twitter = None
            server.twitter_notification_enabled = server_data['notif_on']
            server.retweet_activated = server_data['retweet_notif_on']
            models.session.flush()
            models.session.commit()
        session['twitter_account_updated'] = True
        return str(data)


@app.route('/sociabot/twitch')
@login_required
def twitch():
    """The twitch configuration page
    """
    twitch_login_url = twitch_func.get_twitch_login_url_handmade()
    if session.get('twitch_token') is not None:
        twitch = OAuth2Session(
            twitch_func.twitch_client_id, token=session['twitch_token'])
        # get twitch user info
        twitch_user_info = twitch_func.get_twitch_infos(twitch)
        if type(twitch_user_info) == dict:
            discord = OAuth2Session(client_id, token=session['discord_token'])
            user_info = discord_func.user_infos(discord)
            avatar = discord.get(discord_cdn + 'avatars/' +
                                 user_info['id'] + '/' + user_info['avatar']
                                 + '.png')
            user_guilds = discord.get(
                base_discord_api_url + '/users/@me/guilds').json()
            owned_guilds, bot_owned_guilds = discord_func.own_guilds(
                user_guilds)
            # get twitch accounts linked to user
            twitch_accounts = models.session.query(
                models.TwitchAccount).filter(
                models.TwitchAccount.user_id == session['user_id']
            ).all()
            # twitch accounts json
            twitch_accounts_json = []
            for twitch_account in twitch_accounts:
                twitch_accounts_json.append(twitch_account._json())
            # get all guild where user is the admin
            bot_user_guilds = models.session.query(models.Server).filter(
                models.Server.admin_id == str(session['user_id'])
            ).all()
            # get all channels for the guilds
            channels = discord_func.get_text_channels_for_user(
                bot_user_guilds)
            # get guilds json
            bot_user_guilds_json = []
            for bot_user_guild in bot_user_guilds:
                bot_user_guilds_json.append(bot_user_guild._json())
            return render_template(
                "twitch.html",
                black_theme=session['black_theme'],
                twitch_login_url=twitch_login_url,
                twitch_account=twitch_user_info,
                owned_guilds=bot_owned_guilds,
                avatar_url=avatar.url,
                twitch_accounts=twitch_accounts_json,
                channels=channels,
                bot_user_guilds=bot_user_guilds_json,
            )
        else:
            return twitch_user_info
    else:
        return redirect(twitch_login_url)


@app.route('/sociabot/oauth_callback_twitch')
@login_required
def oauth_callback_twitch():
    """Callback url for twitch authentification
    """
    token = twitch_func.get_twitch_token_handmade()
    session['twitch_token'] = token
    twitch = OAuth2Session(
        twitch_func.twitch_client_id, token=session['twitch_token'])
    user_id = str(session['user_id'])
    twitch_user_info = twitch_func.get_twitch_infos(twitch)
    existing_user = models.session.query(models.User).filter(
        models.User.id == user_id).first()
    account = models.session.query(models.TwitchAccount).filter(
        models.TwitchAccount.twitch_id == twitch_user_info['id']
    ).first()
    if account is None:
        twitch_func.add_twitch_account(existing_user, twitch)
        session['twitch_account_added'] = True
    else:
        account.twitch_access_token = session[
            'twitch_token']['access_token']
        models.session.flush()
        models.session.commit()
        session['twitch_account_exist'] = True
    return redirect(url_for('twitch'))


@app.route('/sociabot/twitch_update_info', methods=['POST'])
@login_required
def twitch_update_info():
    """View used only in POST to get data from twitch configuration page
    """
    if request.method == "POST":
        data = request.json
        for server_data in data:
            server = models.session.query(models.Server).filter(
                models.Server.server_id == str(server_data['server_id'])
            ).first()
            try:
                if not (server_data['twitch_account_id'] == "None" or
                        server_data['twitch_account_id'] is None):
                    server.twitch_account_linked = int(
                        server_data['twitch_account_id'])
                    if server_data['notif_on']:
                        twitch_func.twitch_stream_set_webhook(
                            server_data['twitch_account_id'], "unsubscribe")
                        webhook = models.session.query(
                            models.TwitchAccountWebhook
                        ).filter(
                            models.TwitchAccountWebhook.twitch_id ==
                            server_data['twitch_account_id']
                        ).filter(models.TwitchAccountWebhook.server_id ==
                                 server_data['server_id']
                                 ).first()
                        if webhook is not None:
                            models.session.delete(webhook)
                            models.session.commit()
                    else:
                        twitch_func.twitch_stream_set_webhook(
                            server_data['twitch_account_id'], "subscribe")
                        webhook = models.session.query(
                            models.TwitchAccountWebhook
                        ).filter(
                            models.TwitchAccountWebhook.twitch_id ==
                            server_data['twitch_account_id']
                        ).filter(models.TwitchAccountWebhook.server_id ==
                                 server_data['server_id']
                                 ).all()
                        if webhook is not None:
                            webhook_obj = models.TwitchAccountWebhook(
                                server_id=server_data['server_id'],
                                twitch_id=server_data['twitch_account_id']
                            )
                            models.session.add(webhook_obj)
                            models.session.commit()
            except KeyError:
                server.twitch_account_linked = None
            try:
                if not (server_data['notif_id'] == "None" or
                        server_data['notif_id'] is None):
                    server.notification_channel_twitch = str(
                        server_data['notif_id'])
            except KeyError:
                server.notification_channel_twitch = None
            server.twitch_notification_enabled = server_data['notif_on']
            models.session.flush()
            models.session.commit()
        session['twitch_account_updated'] = True
        return str(data)


@app.route('/sociabot/stream_webhook', methods=['POST', 'GET'])
def twitch_get_stream_notif():
    if request.method == "GET":
        return request.args.get('hub.challenge')
    else:
        webhooks = models.session.query(models.TwitchAccountWebhook).filter(
            models.TwitchAccountWebhook.twitch_id == request.json[
                'data'][0]['user_id']
        ).all()
        for webhook in webhooks:
            webhook.new_notif = True
        return "ok"


@app.route('/sociabot/profile')
@login_required
def profile():
    """
    User profile page
    Used to Invite/Exclude bot from server
    Used to see user personnal informations.
    """
    discord = OAuth2Session(client_id, token=session['discord_token'])
    user_info = discord_func.user_infos(discord)
    avatar = discord.get(discord_cdn + 'avatars/' +
                         user_info['id'] + '/' + user_info['avatar'] + '.png')
    user_guilds = discord.get(
        base_discord_api_url + '/users/@me/guilds').json()
    owned_guilds, bot_owned_guilds = discord_func.own_guilds(user_guilds)
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


@app.route('/sociabot/bot-server-added')
@login_required
def bot_server_added():
    session['bot_server_added'] = True
    return redirect(url_for('profile'))


@app.route("/invite_to/<server_name>")
@login_required
def invite_bot_to(server_name):
    server_name = unquote(server_name)
    return redirect(url_for('index'))


@app.route('/sociabot/blacktheme/<enabled>/<actualUrl>')
@login_required
def black_theme(enabled, actualUrl):
    """Toogle black theme

    Arguments:
        enabled {str} -- Is the black theme enabled
        actualUrl {url} -- Actual url to redirect
    """
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
