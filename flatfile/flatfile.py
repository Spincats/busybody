import sys
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def get_last(config):
    if "log_directory" not in config["persistence"] or not config["persistence"]["log_directory"]:
        raise RuntimeError("Flat file persistence requested, but no log_directory specified.")
    log_dir = Path(config["persistence"]["log_directory"])
    log_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
    modules = set()
    if "pollers" in config and config["pollers"]:
        modules.update(config["active_modules"]["pollers"])
    if "analysis" in config and config["analysis"]:
        modules.update(config["active_modules"]["analysis"])
    for module in modules:
        config_mod = getattr(sys.modules[module], module)
        ts_field = config_mod.TIMESTAMP_FIELD
        log_file = log_dir / (module + ".log")
        log_file.touch(mode=0o660, exist_ok=True)
        last = ""
        with log_file.open('r') as f:
            for line in f:
                if len(line) > 3:
                    last = line
        if "last_polled" not in config:
            config["last_polled"] = {}
        config["last_polled"][module] = {}
        if last:
            last_event = json.loads(last)
            config["last_polled"][module]["last_polled_time"] = last_event[ts_field]
            config["last_polled"][module]["last_polled_event"] = last_event
        else:
            config["last_polled"][module]["last_polled_time"] = 0
            config["last_polled"][module]["last_polled_event"] = {}
    return config


def persist(config, data):
    if "log_directory" not in config["persistence"] or not config["persistence"]["log_directory"]:
        raise RuntimeError("Flat file persistence requested, but no log_directory specified.")
    log_dir = Path(config["persistence"]["log_directory"])
    log_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
    for module in data:
        log_file = log_dir / (module + ".log")
        log_file.touch(mode=0o660, exist_ok=True)
        with log_file.open('a') as f:
            for entry in data[module]:
                f.write('%s\n' % json.dumps(entry))


def get_historical_data(config):
    data = {}
    if "log_directory" not in config["persistence"] or not config["persistence"]["log_directory"]:
        raise RuntimeError("Flat file persistence requested, but no log_directory specified.")
    log_dir = Path(config["persistence"]["log_directory"])
    log_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
    if "analysis" not in config:
        return data
    for module in config["active_modules"]["analysis"]:
        data[module] = []
        analysis_mod = getattr(sys.modules[module], module)
        ts_field = analysis_mod.TIMESTAMP_FIELD
        if "history_limit" in config:
            last_time = config["last_polled"][module]["last_polled_time"]
            if type(last_time) == str and "T" in last_time:
                last_time = datetime.timestamp(datetime.strptime(last_time, '%Y-%m-%dT%H:%M:%S.%fZ'))
            limit = max(0, last_time - config["history_limit"])
        else:
            limit = 0
        log_file = log_dir / (module + ".log")
        log_file.touch(mode=0o660, exist_ok=True)
        with log_file.open('r') as f:
            for line in f:
                event = json.loads(line)
                timestamp = event[ts_field]
                if type(timestamp) == str and "T" in timestamp:
                    timestamp = datetime.timestamp(datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ'))
                if str(timestamp) >= str(limit):
                    data[module].append(event)
    return data


def get_last_analyzed(config):
    if "log_directory" not in config["persistence"] or not config["persistence"]["log_directory"]:
        raise RuntimeError("Flat file persistence requested, but no log_directory specified.")
    log_dir = Path(config["persistence"]["log_directory"])
    log_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
    log_file = log_dir / "last_analyzed.log"
    log_file.touch(mode=0o660, exist_ok=True)
    with log_file.open('r') as f:
        try:
            timestamp = json.load(f)
        except:
            timestamp = 0
    return timestamp


def persist_last_analyzed(config, timestamp):
    if "log_directory" not in config["persistence"] or not config["persistence"]["log_directory"]:
        raise RuntimeError("Flat file persistence requested, but no log_directory specified.")
    log_dir = Path(config["persistence"]["log_directory"])
    log_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
    log_file = log_dir / "last_analyzed.log"
    log_file.touch(mode=0o660, exist_ok=True)
    with log_file.open('w') as f:
        json.dump(timestamp, f)
