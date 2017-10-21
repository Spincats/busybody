import logging
from collections import Iterable
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)


TIMESTAMP_FIELD = "id.time"
USER_FIELD = "actor.email"
IP_FIELD = "ipAddress"
USER_AGENT_FIELD = "events.0.login_type"
FILTER_FIELD = "events.0.name"
FILTERED_EVENTS = ["login_failure"]


def poll(config):
    data = []
    scopes = ['https://www.googleapis.com/auth/admin.reports.audit.readonly']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(config["pollers"]["gsuite"]["credential_file"], scopes=scopes)
    credentials = credentials.create_delegated(config["pollers"]["gsuite"]["admin_email"])
    service = discovery.build('admin', 'reports_v1', credentials=credentials)
    request = service.activities().list(userKey='all', applicationName='login')
    for i in range(1, 101):
        logger.info("Polling page %s..." % i)
        results = request.execute()
        activities = results.get('items', [])
        for event in activities:
            flattened = flatten(event)
            if flattened[TIMESTAMP_FIELD] > str(config["last_polled"]["gsuite"]["last_polled_time"]):
                data.append(flattened)
            elif flattened[TIMESTAMP_FIELD] == str(config["last_polled"]["gsuite"]["last_polled_time"]):
                if flattened["id.uniqueQualifier"] == config["last_polled"]["gsuite"]["last_polled_event"]["id.uniqueQualifier"]:
                    caught_up = True
                    break
                else:
                    data.append(flattened)
            else:
                caught_up = True
                break
        request = service.activities().list_next(request, results)
        if caught_up or request is None:
            break
    return data


def notify(config, alerts):
    return


def flatten(event, prefix=''):
    flattened = {}
    for field_no, field in enumerate(event):
        if 'keys' in dir(event):
            # Special case "parameters" values. We should to treat those as dicts.
            if field == "parameters":
                for param in event[field]:
                    if isinstance(param["value"], Iterable) and not isinstance(param["value"], str):
                        flattened.update(param["value"], prefix + param["name"] + ".")
                    else:
                        flattened[prefix + param["name"]] = param["value"]
                continue
            else:
                nextLevel = event[field]
                currEntry = prefix + str(field)
        else:
            nextLevel = event[field_no]
            currEntry = prefix + str(field_no)
        if isinstance(nextLevel, Iterable) and not isinstance(nextLevel, str):
            flattened.update(flatten(nextLevel, currEntry + "."))
        else:
            flattened[currEntry] = nextLevel
    return flattened
