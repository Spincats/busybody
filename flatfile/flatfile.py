import sys
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_last(config):
    if "log_directory" not in config["persistence"] or not config["persistence"]["log_directory"]:
        raise RuntimeError("Flat file persistence requested, but no log_directory specified.")
    log_dir = Path(config["persistence"]["log_directory"])
    log_dir.mkdir(mode=0o775, parents=True, exist_ok=True)
    if "pollers" in config and config["pollers"]:
        for module in config["active_modules"]["pollers"]:
            poll_mod = getattr(sys.modules[module], module)
            ts_field = poll_mod.TIMESTAMP_FIELD
            log_file = log_dir / (module + ".log")
            log_file.touch(mode=0o660, exist_ok=True)
            last = ""
            with log_file.open('r') as f:
                for line in f:
                    if len(line) > 3:
                        last = line
            if last:
                last_event = json.loads(last)
                config["pollers"][module]["last_polled_time"] = last_event[ts_field]
                config["pollers"][module]["last_polled_event"] = last_event
            else:
                config["pollers"][module]["last_polled_time"] = 0
                config["pollers"][module]["last_polled_event"] = {}
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
    if not "pollers" in config:
        return data
    for module in config["active_modules"]["pollers"]:
        data[module] = []
        poll_mod = getattr(sys.modules[module], module)
        ts_field = poll_mod.TIMESTAMP_FIELD
        if "history_limit" in config:
            limit = max(0, config["pollers"][module]["last_polled_time"] - config["history_limit"])
        else:
            limit = 0
        log_file = log_dir / (module + ".log")
        log_file.touch(mode=0o660, exist_ok=True)
        with log_file.open('r') as f:
            for line in f:
                event = json.loads(line)
                if str(event[ts_field]) >= str(limit):
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
