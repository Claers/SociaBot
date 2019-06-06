from requests_oauthlib import OAuth2Session
from flask import request, session, redirect, url_for

import cogs.utils.models as models
import cogs.utils.settings as settings
import website

base_discord_api_url = 'https://discordapp.com/api'
discord_cdn = "https://cdn.discordapp.com/"
scope = ['identify', 'email', 'connections', 'guilds']
token_url = 'https://discordapp.com/api/oauth2/token'
authorize_url = 'https://discordapp.com/api/oauth2/authorize'

client_id = settings.discord_client_id
client_secret = settings.discord_client_secret


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
                guild.discord_admin_id = user.discord_user_id
    # set user connected guild in DataBase
    for discord_guild in discord_guilds:
        user.discord_guild_ids.append(discord_guild)
    models.session.flush()
    models.session.commit()
    # create data into the session
    website.get_user(discord)
