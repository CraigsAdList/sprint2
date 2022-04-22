# pylint: disable=W0611, W0107, W0613
# first two warning are disabled for starter code, we should enable them later.
# 3rd is about unused variable in 'def load_user(user_id):', maybe we can fix it

"""Module for running flask and setting up endpoints"""

import os


import flask

from flask_login import current_user, login_user, logout_user, LoginManager

from flask import Response, render_template, request
from sqlalchemy import true

from db_utils import (
    createAd,
    deleteAllAds,
    getAdsByOwnerEmail,
    getAllAccounts,
    getAllAds,
    get_ads,
    get_channels,
)

from werkzeug.security import generate_password_hash, check_password_hash

from dotenv import load_dotenv, find_dotenv

from models import db, Account, Ad, Channel

load_dotenv(find_dotenv())

app = flask.Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.getenv("SECRET_KEY")

db.init_app(app)
with app.app_context():

    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    """Stolen from some tutorial on flask-login. While it is not explicitly used
    here, it is required by flask-login"""
    return Account.query.get(int(user_id))


# set up a separate route to serve the index.html file generated
# by create-react-app/npm run build.
# By doing this, we make it so you can paste in all your old app routes
# from Milestone 2 without interfering with the functionality here.
bp = flask.Blueprint(
    "bp",
    __name__,
    template_folder="./static/react",
)


# route for serving React page
@bp.route("/")
@bp.route("/ads")
@bp.route("/channels")
@bp.route("/login")
@bp.route("/signup")
@bp.route("/acount")
@bp.route("/new_add")
@bp.route("/new_channel")
@bp.route("/new_response")
@bp.route("/new_offer")
def index():
    """Root endpoint"""
    # NB: DO NOT add an "index.html" file in your normal templates folder
    # Flask will stop serving this React page correctly
    return flask.render_template("index.html")


@bp.route("/handle_login", methods=["POST"])
def handle_login():
    """Handle login"""
    if flask.request.method == "POST":
        user = Account.query.filter_by(email=flask.request.json["email"]).first()
        if user != None and check_password_hash(
            user.password, flask.request.json["password"]
        ):
            is_login_successful = login_user(user)
            return flask.jsonify(
                {"is_login_successful": is_login_successful, "error_message": ""}
            )
        # if password is incorrect
        elif user != None and not check_password_hash(
            user.password, flask.request.json["password"]
        ):
            return flask.jsonify(
                {"is_login_successful": False, "error_message": "Incorrect password"}
            )
        # if the email is NOT present in the database, send a message saying “there is no user with this email”
        # and give a link to sign up page
        elif user == None:
            return flask.jsonify(
                {
                    "is_login_successful": False,
                    "error_message": "No user with this email",
                }
            )


@bp.route("/handle_signup", methods=["POST"])
def handle_signup():
    """Handle signup"""
    if flask.request.method == "POST":
        u = Account.query.filter_by(username=flask.request.json["username"]).first()
        if u is None:
            user = Account(
                username=flask.request.json["username"],
                email=flask.request.json["email"],
                password=generate_password_hash(flask.request.json["password"]),
                channel_owner=flask.request.json["channel_owner"],
            )
            db.session.add(user)
            db.session.commit()
            new_user = Account.query.filter_by(
                email=flask.request.json["email"]
            ).first()
            is_signup_successful = new_user is not None
            return flask.jsonify(
                {"is_signup_successful": is_signup_successful, "error_message": ""}
            )
        elif (
            flask.request.json["username"] == ""
            or flask.request.json["email"] == ""
            or flask.request.json["password"] == ""
        ):
            return flask.jsonify(
                {
                    "is_signup_successful": False,
                    "error_message": "Fill in all the required data",
                }
            )
        elif u is not None:
            return flask.jsonify(
                {
                    "is_signup_successful": False,
                    "error_message": "A user with such username/email already exists",
                }
            )


@bp.route("/handle_logout", methods=["POST"])
def handle_logout():
    logout_user()
    return is_logged_in()


@bp.route("/channelowner", methods=["GET"])
def is_channel_owner():
    """returns true if current user is a channel owner"""
    return flask.jsonify({"is_user_channel_owner": current_user.channel_owner})


@app.route("/getaccounts", methods=["GET"])
def getAccounts():
    return flask.jsonify({"accounts": getAllAccounts()})


@bp.route("/is_logged_in", methods=["GET"])
def is_logged_in():
    """checks whether a user is logged in"""
    if current_user.is_authenticated == True:
        return flask.jsonify({"isuserloggedin": True})
    else:
        return flask.jsonify({"isuserloggedin": False})

@bp.route("/get_current_user", methods=["GET"])
def get_current_user():
    """returns current logged in user"""
    return flask.jsonify({"current_user":current_user.username})



@bp.route("/account_info", methods=["GET", "POST"])
def account_info():
    """Return current user's JSON data"""
    current_account = current_user.username
    account = Account.query.filter_by(username=current_account).first()
    adLog = Ad.query.filter_by(account_id=account.id).all()
    channelLog = Channel.query.filter_by(account_id=account.id).all()
    adList = []
    for i in adLog:
        adDict = {}
        adDict["title"] = i.title
        adDict["topics"] = i.topics
        adDict["text"] = i.text
        adDict["reward"] = i.reward
        adList.append(adDict)
    channelList = []
    for i in channelLog:
        channelDict = {}
        channelDict["channel_name"] = i.channel_name
        channelDict["subscribers"] = i.subscribers
        channelDict["topics"] = i.topics
        channelDict["preferred_reward"] = i.preferred_reward
        channelList.append(channelDict)
    return flask.jsonify(
        {"account": current_account, "ads": adList, "channels": channelList}
    )


@bp.route("/return_ads", methods=["GET"])
def return_ads():
    """Returns JSON with ads"""
    args = flask.request.args
    if args.get("for") == "adsPage":
        # return ads for ads page, filtered according to args
        # trying to jsonify a list of channel objects gives an error
        return flask.jsonify(
            {
                "success": True,
                "adsData": get_ads(args),
            }
        )
    return flask.jsonify({"ads": getAllAds()})

@bp.route("/return_selected_channel", methods=["GET"])
def get_channels_by_id():
    """get channels by id"""
    args = flask.request.args
    channel = Channel.query.filter_by(owner_id=args.get("id")).first()
    return flask.jsonify(
            {
                    "id": channel.id,
                    "ownerName": Account.query.filter_by(id=channel.owner_id).first().username,
                    "channelName": channel.channel_name,
                    "subscribers": channel.subscribers,
                    "topics": channel.topics,
                    "preferredReward": channel.preferred_reward,
                }
        )
@bp.route("/return_selected_ads", methods=["GET"])
def get_ads_by_id():
    """get channels by id"""
    args = flask.request.args
    ad = Ad.query.filter_by(owner_id=args.get("id")).first()
    return flask.jsonify(
                {
                    "creator_id": ad.creator_id,
                    "title": ad.title,
                    "topics": ad.topics,
                    "text": ad.text,
                    "reward": ad.reward,
                    "show_in_list": ad.show_in_list,
                }
        )

@bp.route("/return_channels", methods=["GET"])
def return_channels():
    """Returns JSON with channels"""
    args = flask.request.args
    if args.get("for") == "channelsPage":
        # return channels for channels page, filtered acording to args
        # trying to jsonify a list of channel objects gives an error
        return flask.jsonify(
            {
                "success": True,
                "channelsData": get_channels(args),
            }
        )
    return flask.jsonify({"success": False})


@bp.route("/add_channel", methods=["POST"])
def add_channel():
    """Add channel info to database (in the first sprint it can be done only on signup)"""
    pass


@bp.route("/add_Ad", methods=["POST"])
def add_ad():
    if flask.request.method == "POST":
        u = Ad.query.filter_by(title=flask.request.json["title"]).first()
        if u is None:
            ad = Ad(
                title=flask.request.json["title"],
                topics=flask.request.json["topics"],
                text=flask.request.json["text"],
                reward=flask.request.json["reward"],
                show_in_list=flask.request.json["show_in_list"],
            )
            db.session.add(ad)
            db.session.commit()
            new_Ad = Ad.query.filter_by(topics=flask.request.json["topics"]).first()
            add_Ads_succesful = new_Ad is not None
            return flask.jsonify(
                {"add_Ads_succesful": add_Ads_succesful, "error_message": ""}
            )
        elif (
            flask.request.json["title"] == ""
            or flask.request.json["topics"] == ""
            or flask.request.json["text"] == ""
            or flask.request.json["reward"] == ""
            or flask.request.json["show_in_list"] == ""
        ):
            return flask.jsonify(
                {
                    "add_Ads_succesful": False,
                    "error_message": "Fill in all the required data",
                }
            )
        elif u is not None:
            return flask.jsonify(
                {
                    "add_Ads_succesful": False,
                    "error_message": "An Ad with such title already exists",
                }
            )


@bp.route("/get_Ad", methods=["GET", "POST"])
def get_ad():

    ad_log = Ad.query.filter_by(title=Ad.title).all()
    ad_log_data = []
    for ad in ad_log:
        ad_log_data.append(
            {
                "id": ad.id,
                "title": ad.title,
                "topics": ad.topics,
                "text": ad.text,
                "reward": ad.reward,
                "show_in_list": ad.show_in_list,
            }
        )
    return flask.jsonify({"ad": ad_log_data})


@bp.route("/make_response", methods=["POST"])
def make_response():
    if flask.request.method == "POST":
        current_user_id = current_user.id
        ad_log = Ad.query.filter_by(id=id).all()
        ad_log_data = []
        for ad in ad_log:
            ad_log_data.append(
                {
                    "id": ad.id,
                    "title": ad.title,
                    "topics": ad.topics,
                    "text": ad.text,
                    "reward": ad.reward,
                }
            )
        channel_log = Channel.query.filter_by(id=current_user_id).all()
        channel_log_data = []
        for channel in channel_log:

            channel_log_data.append(
                {
                    "id": channel.id,
                    "channelName": channel.channel_name,
                    "subscribers": channel.subscribers,
                    "topics": channel.topics,
                    "preferredReward": channel.preferred_reward,
                }
            )
            if channel_log_data["preferrerdReward"] < ad_log_data["reward"]:
                return flask.jsonify(
                    {"make_response_succesful": True, "error_message": ""}
                )
            else:
                return flask.jsonify(
                    {"make_response_succesful": False, "error_message": ""}
                )
    return flask.jsomify(
        {"ad_log_data": ad_log_data, "channel_log_data": channel_log_data}
    )


@bp.route("/ad_offers", methods=["POST"])
def ad_offers():
    if flask.request.method == "POST":
        current_user_id = current_user.id
        channel_log = Channel.query.filter_by(id=current_user_id).all()
        channel_log_data = []
        for channel in channel_log:
            channel_log_data.append(
                {
                    "id": channel.id,
                    "channelName": channel.channel_name,
                    "subscribers": channel.subscribers,
                    "topics": channel.topics,
                    "preferredReward": channel.preferred_reward,
                }
            )
        ad_log = Ad.query.filter_by(id=current_user_id).all()
        ad_log_data = []
        for ad in ad_log:
            ad_log_data.append(
                {
                    "id": ad.id,
                    "title": ad.title,
                    "topics": ad.topics,
                    "text": ad.text,
                    "reward": ad.reward,
                }
            )
            if channel_log_data["preferrerdReward"] > ad_log_data["reward"]:
                return flask.jsonify(
                    {"make_response_succesful": True, "error_message": ""}
                )
            else:
                return flask.jsonify(
                    {"make_response_succesful": False, "error_message": ""}
                )
    return flask.jsonify(
        {"ad_log_data": ad_log_data, "channel_log_data": channel_log_data}
    )


app.register_blueprint(bp)

if __name__ == "__main__":
    app.run()
