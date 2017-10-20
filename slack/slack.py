import logging
from slackclient import SlackClient

logger = logging.getLogger(__name__)

TIMESTAMP_FIELD = "date_last"
USER_FIELD = "email"
IP_FIELD = "ip"
USER_AGENT_FIELD = "user_agent"
FILTER_FIELD = None


def poll(config):
    slack_api = SlackClient(config["pollers"]["slack"]["api_token"])
    data = []
    caught_up = False
    for i in range(1, 101):
        logger.info("Polling page %s..." % i)
        api_data = slack_api.api_call("team.accessLogs", count=1000, page=i)
        check_api(api_data)
        for event in api_data["logins"]:
            if event[TIMESTAMP_FIELD] > config["pollers"]["slack"]["last_polled_time"]:
                data.append(event)
            elif event[TIMESTAMP_FIELD] == config["pollers"]["slack"]["last_polled_time"]:
                if str(event) == str(config["pollers"]["slack"]["last_polled_event"]):
                    caught_up = True
                    break
                else:
                    data.append(event)
            else:
                caught_up = True
                break
        if caught_up:
            break
    data = enrich(config, data)
    return data


def notify(config, alerts):
    return


def check_api(data):
    if not data["ok"]:
        raise RuntimeError("Slack API returned an error: "+str(data))
    else:
        return

def enrich(config, data):
    unique_users = list(set([e["user_id"] for e in data]))
    slack_api = SlackClient(config["pollers"]["slack"]["api_token"])
    user_map = {}

    for user in unique_users:
        user_info = slack_api.api_call("users.info", user=user)
        check_api(user_info)
        logger.debug(user_info)
        if "is_bot" in user_info["user"] and user_info["user"]["is_bot"]:
            continue
        elif "is_app_user" in user_info["user"] and user_info["user"]["is_app_user"]:
            continue
        elif "profile" in user_info["user"] and "email" in user_info["user"]["profile"]:
            user_map[user] = user_info["user"]["profile"]["email"]
            logger.debug("Mapping user %s to %s." % (user, user_map[user]))
    new_data = []    
    for entry in data:
        if entry["user_id"] in user_map:
            entry["email"] = user_map[entry["user_id"]]
            new_data.append(entry)
    logger.debug("Returning %s records." % len(new_data))
    return new_data
