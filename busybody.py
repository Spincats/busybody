#!env python
import os
import sys
import argparse
import yaml
import logging
from pathlib import Path
import importlib
import re
import geoip2.database
from datetime import datetime
import numpy
from scipy.sparse import hstack
from sklearn.preprocessing import scale
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import IsolationForest

program_version = "1.0"

logger = logging.getLogger(__name__)


def poll(config):
    data = {}
    if "persistence" in config["active_modules"] and config["active_modules"]["persistence"]:
        persist_module = getattr(sys.modules[config["active_modules"]["persistence"]],
                                 config["active_modules"]["persistence"])
        get_last_func = getattr(persist_module, "get_last")
        persist_func = getattr(persist_module, "persist")
        config = get_last_func(config)
    for poller in config["active_modules"]["pollers"]:
        poll_mod = getattr(sys.modules[poller], poller)
        ts_field = poll_mod.TIMESTAMP_FIELD
        poll_func = getattr(poll_mod, "poll")
        logger.info("Polling %s for new events..." % poller)
        data[poller] = poll_func(config)
        data[poller].sort(key=lambda k: k[ts_field])
    if "persistence" in config["active_modules"] and config["active_modules"]["persistence"]:
        persist_func(config, data)
    return


def load_historical(config):
    if "persistence" in config["active_modules"] and config["active_modules"]["persistence"]:
        persist_module = getattr(sys.modules[config["active_modules"]["persistence"]],
                                 config["active_modules"]["persistence"])
        get_last_func = getattr(persist_module, "get_last")
        config = get_last_func(config)
        get_historical_func = getattr(persist_module, "get_historical_data")
        data = get_historical_func(config)
    return data


def preprocess(config, data):
    processed = []
    ua_filter = re.compile('[a-zA-Z:\._\(\)-]*([0-9]+[a-zA-Z:\._\(\)-]*)+')
    for module in data:
        poll_mod = getattr(sys.modules[module], module)
        ts_field = poll_mod.TIMESTAMP_FIELD
        user_field = poll_mod.USER_FIELD
        ip_field = poll_mod.IP_FIELD
        ua_field = poll_mod.USER_AGENT_FIELD
        filter_field = poll_mod.FILTER_FIELD
        city_lookup = geoip2.database.Reader(config["analysis"]["geoip"]["city_db"])
        asn_lookup = geoip2.database.Reader(config["analysis"]["geoip"]["asn_db"])
        for event in data[module]:
            if filter_field:
                if event[filter_field] in poll_mod.FILTERED_EVENTS:
                    continue
            if ts_field not in event or not event[ts_field] or user_field not in event or \
               not event[user_field] or ip_field not in event or not event[ip_field] or \
               ua_field not in event or not event[ua_field]:
                continue
            if type(event[ts_field]) == str:
                ts = datetime.timestamp(datetime.strptime(event[ts_field], '%Y-%m-%dT%H:%M:%S.%fZ'))
            else:
                ts = event[ts_field]
            if "user_map" in config["analysis"][module] and \
               event[user_field] in config["analysis"][module]["user_map"]:
                user = config["analysis"][module]["user_map"][event[user_field]]
            else:
                user = event[user_field]
            if "user_domain" in config["analysis"][module] and '@' not in user:
                user = "@".join((user, config["analysis"][module]["user_domain"]))
            user_agent = ua_filter.sub('', event[ua_field])
            if event[ip_field] is None:
                continue
            city = city_lookup.city(event[ip_field])
            readable = []
            if "en" in city.city.names and city.city.names["en"]:
                readable.append(city.city.names["en"])
            if city.subdivisions and city.subdivisions[0].iso_code:
                readable.append(city.subdivisions[0].iso_code)
            if city.country and city.country.iso_code:
                readable.append(city.country.iso_code)
            if city.continent and city.continent.code:
                readable.append(city.continent.code)
            event["ip_location"] = ", ".join(readable)
            x, y, z = latlon_to_xyz(city.location.latitude, city.location.longitude)
            try:
                asn = asn_lookup.asn(event[ip_field]).autonomous_system_organization
                event["asn"] = asn
            except geoip2.errors.AddressNotFoundError:
                asn = ""
            if not asn:
                asn = ""
            processed.append([ts, event, user, x, y, z, asn, user_agent])
    return sorted(processed, key=lambda event: event[0])


def analyze(config, data):
    alerts = []
    last_analyzed = 0
    if "persistence" in config["active_modules"] and config["active_modules"]["persistence"]:
        persist_module = getattr(sys.modules[config["active_modules"]["persistence"]],
                                 config["active_modules"]["persistence"])
        last_analyzed_func = getattr(persist_module, "get_last_analyzed")
        persist_analyzed_func = getattr(persist_module, "persist_last_analyzed")
        last_analyzed = last_analyzed_func(config)
    # get unique list of users across data
    unique_users = list(set([e[2] for e in data]))
    logger.debug("Unique users: %s" % len(unique_users))
    for user in unique_users:
        logger.debug("Analyzing data for user %s." % user)
        user_events = numpy.array([e for e in data if e[2] == user])
        if last_analyzed > 0 and user_events[-1][0] < last_analyzed:
            logger.debug("Skipping user as they have no non-analyzed events.")
            continue
        asn_vectorizer = TfidfVectorizer(binary=True)
        ua_vectorizer = TfidfVectorizer(binary=True)
        times = user_events[:, 0:1]
        coords = user_events[:, 3:6]
        logger.debug("Transforming ASNs.")
        asns = asn_vectorizer.fit_transform(user_events[:, 6])
        logger.debug("Transforming User-Agents.")
        uas = ua_vectorizer.fit_transform(user_events[:, 7])
        sparse_mat = numpy.concatenate((times, coords, asns.toarray(), uas.toarray()), axis=1)
        logger.debug("Running Isolation Forest.")
        detector = IsolationForest(n_jobs=-1, contamination=0)
        if last_analyzed == 0 or user_events[0][0] >= last_analyzed:
            detector.fit(sparse_mat[:, 1:])
            predictions = detector.predict(sparse_mat[:, 1:])
        else:
            for counter, event in enumerate(sparse_mat):
                if event[0] < last_analyzed:
                    cutoff = counter
                else:
                    break
            cutoff += 1
            logger.debug("Splitting array of length %s at entry %s" % (len(sparse_mat), cutoff))
            detector.fit(sparse_mat[:cutoff, 1:])
            predictions = detector.predict(sparse_mat[cutoff:, 1:])
        flagged = 0
        for ev_no, prediction in enumerate(predictions):
            if prediction == -1:
                flagged += 1
                alerts.append(user_events[ev_no][1])
        logger.debug("Processed %s: %s of %s flagged." % (user, flagged, len(user_events)))
    if "notifiers" in config["active_modules"]:
        for module in config["active_modules"]["notifiers"]:
            notify_mod = getattr(sys.modules[module], module)
            notify_func = getattr(notify_mod, "notify")
            notify_func(config, alerts)
    else:
        for alert in alerts:
            logger.info(alert)
    persist_analyzed_func(config, data[-1][0])


def latlon_to_xyz(lat, lon):
    phi = (90 - lat) * (numpy.pi / 180)
    theta = (lon + 180) * (numpy.pi / 180)

    x = 0 - (numpy.sin(phi) * numpy.cos(theta))
    z = (numpy.sin(phi) * numpy.sin(theta))
    y = (numpy.cos(phi))

    return (x, y, z)


def load_config(config_path):
    if config_path:
        config_file = Path(config_path)
    else:
        homeconfig = Path.home() / ".config" / "busybody" / "config.yml"
        scriptconfig = Path(os.path.realpath(__file__)).parent / "config.yml"
        if homeconfig.is_file():
            config_file = homeconfig
        elif scriptconfig.is_file():
            config_file = scriptconfig
        else:
            raise RuntimeError("No configuration file found.")
    with config_file.open() as f:
        config = yaml.load(f, Loader=yaml.loader.BaseLoader)
    return config


def load_modules(config):
    config["active_modules"] = {}
    if "pollers" not in config or not config["pollers"]:
        raise RuntimeError("Polllers aren't optional.")
    config["active_modules"]["pollers"] = []
    for poller in config["pollers"]:
        importlib.import_module(poller, poller)
        config["active_modules"]["pollers"].append(poller)
    if config["mode"] is None or config["mode"] == "analyze":
        if "notifiers" not in config or not config["notifiers"]:
            raise RuntimeError("Configured to analyze, but no notifiers in config file.")
        config["active_modules"]["notifiers"] = []
        for notifier in config["notifiers"]:
            importlib.import_module(notifier, notifier)
            config["active_modules"]["notifiers"].append(notifier)
    if "persistence" in config and config["persistence"]:
        if "module" in config["persistence"] and config["persistence"]["module"]:
            importlib.import_module(config["persistence"]["module"],
                                    config["persistence"]["module"])
            config["active_modules"]["persistence"] = config["persistence"]["module"]
        else:
            raise RuntimeError("Persistence is configured, but no module specified.")
    return config


# INIT STUFF/CONTROL LOOP
if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="Busybody",
                                     description="Neighborhood watch for your SaaS apps.")
    parser.add_argument("-c", "--config", default=None,
                        help="Non-standard location of a configuration file.")
    parser.add_argument("-f", "--file", default=None,
                        help="File to redirect log output into.")
    parser.add_argument("-m", "--mode", default=None,
                        help="Select a mode from: poll, analyze. Default is to perform both.")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase log verbosity level. (Default" +
                             " level: WARN, use twice for DEBUG)")
    parser.add_argument("-V", "--version", action="version",
                        version="%(prog)s " + program_version,
                        help="Display version information and exit.")
    args = parser.parse_args()
    loglevel = max(10, 30 - (args.verbose * 10))
    logformat = '%(asctime)s %(levelname)s: %(message)s'
    if args.file:
        logging.basicConfig(filename=args.file, level=loglevel, format=logformat)
    else:
        logging.basicConfig(level=loglevel, format=logformat)

    logger.info("Starting busybody...")
    try:
        config = load_config(args.config)
        config["mode"] = args.mode
        config = load_modules(config)
        logger.info("Modules and config loaded.")
        if not args.mode or args.mode == "poll":
            logger.info("Polling for new events...")
            data = poll(config)
        if not args.mode or args.mode == "analyze":
            if "persistence" in config and config["persistence"]:
                logger.info("Loading stored data...")
                data = load_historical(config)
            logger.info("Preprocessing data...")
            data = preprocess(config, data)
            logger.info("Analyzing data...")
            analyze(config, data)
    except Exception as e:
        raise(e)
    finally:
        logger.info("Busybody closing.")
        logging.shutdown()
