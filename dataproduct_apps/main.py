#!/usr/bin/env python
import logging
import signal

from fiaas_logging import init_logging

from dataproduct_apps import kafka
from dataproduct_apps.config import Settings
from dataproduct_apps.endpoints import start_server


class ExitOnSignal(Exception):
    pass


def signal_handler(signum, frame):
    raise ExitOnSignal()


def _topic_action(settings: Settings):
    from dataproduct_apps import topics as _t

    topics = _t.collect_topics()
    _t.write_file_to_cloud_storage(settings, topics)
    taas = _t.generate_topic_accesses(settings, topics)
    kafka.publish(settings, taas, settings.topic_topic)


def topics():
    return _main(_topic_action)


def _collect_action(settings: Settings):
    from dataproduct_apps import collect as _c, kafka

    apps = _c.collect_data(settings)
    kafka.publish(settings, apps, settings.app_topic)


def collect():
    return _main(_collect_action)


def _persist_action(settings: Settings):
    from dataproduct_apps import persist as _p
    _, ec = _p.run(settings)
    return int(ec > 0)


def persist():
    return _main(_persist_action)


def _main(action):
    settings = Settings()
    _init_logging(settings)
    server = start_server()
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)
        try:
            return action(settings)
        except ExitOnSignal:
            return 0
        except Exception as e:
            logging.exception(f"unwanted exception: {e}")
            return 113
    finally:
        server.shutdown()


def _init_logging(settings: Settings):
    if settings.running_in_nais:
        init_logging(format="json")
    else:
        init_logging(debug=True)
    logging.getLogger("werkzeug").setLevel(logging.WARN)
