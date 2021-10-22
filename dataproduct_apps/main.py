#!/usr/bin/env python
import os
import signal
import time
import logging

from fiaas_logging import init_logging

from dataproduct_apps.endpoints import start_server


class ExitOnSignal(Exception):
    pass


def signal_handler(signum, frame):
    raise ExitOnSignal()


def main():
    _init_logging()
    server = start_server()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)
    try:
        time.sleep(120)  # TODO: Do stuff here
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


if __name__ == '__main__':
    main()
