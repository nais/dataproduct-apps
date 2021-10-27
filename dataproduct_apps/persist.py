import logging

from dataproduct_apps import kafka


LOG = logging.getLogger(__name__)


def run_forever():
    for app in kafka.receive():
        LOG.info("app: %s", app)
