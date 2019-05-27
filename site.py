from flask import Flask
from flask import g, session, request, url_for, flash
from flask import redirect, render_template
from requests_oauthlib import OAuth1Session


app = Flask(__name__)
app.debug = True
app.secret_key = 'development'

consumer_key = ''
consumer_secret = ''
global ro_key_glob
global ro_secret_glob


def get_resource_token():
    # create an object of OAuth1Session
    request_token = OAuth1Session(
        client_key=consumer_key,
        client_secret=consumer_secret,
        callback_uri="http://localhost:5000/return")
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
    oauth_token = OAuth1Session(client_key=consumer_key,
                                client_secret=consumer_secret,
                                resource_owner_key=ro_key,
                                resource_owner_secret=ro_secret)
    url = 'https://api.twitter.com/oauth/access_token'
    data = {"oauth_verifier": verifier}

    access_token_data = oauth_token.post(url, data=data)
    print(access_token_data.text)
    access_token_list = str.split(access_token_data.text, '&')
    return access_token_list


@app.route('/')
def index():
    global ro_key_glob
    global ro_secret_glob
    resource = get_resource_token()
    ro_key_glob = resource[0]
    ro_secret_glob = resource[1]
    return("<a href=https://api.twitter.com/oauth/authenticate?oauth_token=" +
           str(resource[0]) + "> Lien </a>")


@app.route('/return')
def return_twitter():
    global ro_key_glob
    global ro_secret_glob
    token = request.args.get('oauth_token')
    verifier = request.args.get('oauth_verifier')
    access = twitter_get_access_token(verifier, ro_key_glob, ro_secret_glob)
    return(str(access))


if __name__ == '__main__':
    app.run()
