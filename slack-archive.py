__author__ = 'jjlehr'

import logging as log
import sys
import os
import yaml
from datetime import datetime
from flask import Flask, url_for
from flask import request
from slacker import Slacker


app = Flask(__name__)
env = dict()
slack = None
inactive_time = 1  # days
bot_username = 'slack-archive'


def is_channel_active(channel, current_datetime):
    ts = channel['latest']['ts']
    last_activity_datetime = datetime.fromtimestamp(float(ts))
    time_delta = current_datetime - last_activity_datetime
    if time_delta.days >= inactive_time:
        return False
    return True


def notify_channel_creator(channel):
    # creator = channel['creator']
    # response = slack.im.open(creator)
    # This is janeklehr b-ailse user id for test purposes
    response = slack.im.open('U03TZ9WNB')
    im_channel = response.body["channel"]["id"]
    message = "#%s has been inactive for %d days or more so it needs to be archived. You may use this " \
              "link to archive it.\n%s%s" % (channel['name'], inactive_time, request.url_root[:-1],
                                             url_for('archive_channel', channel=channel['id']))
    slack.chat.post_message(im_channel, message, username=bot_username)


@app.route('/', methods=['GET', 'POST'])
def run_archive():
    if request.method == "GET":
        return "The archive bot is up and running."
    try:
        inactive_channels = []
        current_datetime = datetime.now()
        response = slack.channels.list(exclude_archived=1)
        channel_ids = [ch['id'] for ch in response.body['channels']]
        channels = [slack.channels.info(ch_id).body['channel'] for ch_id in channel_ids]
        for channel in channels:
            if 'latest' not in channel.keys():
                print("#%s: Cannot find latest message info." % channel['name'])
                continue
            if not is_channel_active(channel, current_datetime):
                print channel['name']
                inactive_channels.append(channel['name'])
                notify_channel_creator(channel)
        return str(inactive_channels)

    except Exception as e:
        print e
        return e


@app.route('/archive', methods=['GET', 'POST'])
def archive_channel():
    channel = request.args.get('channel')
    try:
        slack.channels.archive(channel)
        return "Channel archived successfully."
    except Exception as e:
        return "Error:\n%s" % str(e)

if __name__ == "__main__":
    log.basicConfig(filename='slack-archive.log', level=log.DEBUG, format='%(asctime)s %(levelname)s:%(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S')
    global env, slack
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "local":
            log.info("Try loading from a local env.yaml file")
            env = yaml.load(file("env.yaml"))
            env["HOST"] = 'localhost'
            env["PORT"] = 5000
        else:
            log.info("Loading environment variables from Bluemix")
            env["SLACK_TOKEN"] = os.getenv("SLACK_TOKEN")
            env["SLACK_URL"] = os.getenv("SLACK_URL")
            env["SLACK_ERROR_CHANNEL"] = os.getenv("SLACK_ERROR_CHANNEL")
            env["HOST"] = '0.0.0.0'
            env["PORT"] = os.getenv('VCAP_APP_PORT', '5000')

        slack = Slacker(env['SLACK_TOKEN'])
    except Exception as e:
            log.error("Failed to load the environment \n %s" % e)
            sys.exit(2)
    app.run(host=env["HOST"], port=env["PORT"])
