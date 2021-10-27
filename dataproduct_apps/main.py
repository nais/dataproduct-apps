#!/usr/bin/env python
import logging
import os
import signal

from fiaas_logging import init_logging

from dataproduct_apps.endpoints import start_server


class ExitOnSignal(Exception):
    pass


def signal_handler(signum, frame):
    raise ExitOnSignal()


def collect():
    from dataproduct_apps import collect as _c, kafka

    def action():
        apps = _c.collect_apps()
        kafka.publish(apps)

    _main(action)


def persist():
    from dataproduct_apps import persist as _p
    _main(_p.run_forever)


def _main(action):
    _init_logging()
    server = start_server()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)
    try:
        action()
    except ExitOnSignal:
        pass
    except Exception as e:
        logging.exception(f"unwanted exception: {e}")
    server.shutdown()


def _init_logging():
    if os.getenv("NAIS_CLIENT_ID"):
        init_logging(format="json")
    else:
        init_logging(debug=True)
    logging.getLogger("werkzeug").setLevel(logging.WARN)
