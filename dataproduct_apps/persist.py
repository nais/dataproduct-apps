import time

from dataproduct_apps import kafka


def run_forever():
    while True:
        apps = kafka.receive()
