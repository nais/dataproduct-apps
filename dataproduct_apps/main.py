#!/usr/bin/env python
import logging
import os
import signal

from fiaas_logging import init_logging

from dataproduct_apps import kafka
from dataproduct_apps.endpoints import start_server


class ExitOnSignal(Exception):
    pass


def signal_handler(signum, frame):
    raise ExitOnSignal()


def topics():
    from dataproduct_apps import topics as _t

    def action():
        topics = _t.collect_topics()
        _t.write_file_to_cloud_storage(topics)
        taas = _t.parse_topics(topics)
        kafka.publish(taas, kafka.TOPIC_TOPIC)

    return _main(action)


def collect():
    from dataproduct_apps import collect as _c, kafka

    def action():
        apps = _c.collect_data()
        kafka.publish(apps, kafka.APP_TOPIC)

    return _main(action)


def persist():
    from dataproduct_apps import persist as _p

    def action():
        _, ec = _p.run()
        return int(ec > 0)

    return _main(action)


def _main(action):
    _init_logging()
    server = start_server()
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)
        try:
            exit_code = action()
        except ExitOnSignal:
            exit_code = 0
        except Exception as e:
            logging.exception(f"unwanted exception: {e}")
            exit_code = 113
    finally:
        server.shutdown()
    return exit_code


def _init_logging():
    if os.getenv("NAIS_CLIENT_ID"):
        init_logging(format="json")
    else:
        init_logging(debug=True)
    logging.getLogger("werkzeug").setLevel(logging.WARN)
