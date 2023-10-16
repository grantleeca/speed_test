import argparse
import json
import logging
import socket
import socketserver
import sys
from logging.handlers import RotatingFileHandler

from st_client import TCPClient, UDPClient
from st_server import SpeedTCPHandler, SpeedUDPHandler


def make_logger(level: str, file_name=None):
    formatter = logging.Formatter('%(asctime)s: %(levelname)s %(filename)s %(lineno)d: %(message)s')

    # create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level.upper())

    # create console handler
    handler = logging.StreamHandler(sys.stdout)

    handler.setLevel(level.upper())
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    if file_name:
        # create log file
        handler = RotatingFileHandler(file_name, maxBytes=5 * 1024 * 1024, backupCount=3, delay=True)

        # add formatter to handler
        handler.setLevel(level.upper())
        handler.setFormatter(formatter)

        # add handler to logger
        logger.addHandler(handler)

    return logger


def get_parser():
    parser = argparse.ArgumentParser(description="Speed test for python. version: 0.1")

    model = parser.add_mutually_exclusive_group(required=True)
    model.add_argument('--server', '-s', action="store_true", help='Server model')
    model.add_argument('--client', '-c', action="store_true", help='Client model')

    parser.add_argument('--config', default='config.json', help='Log file name')

    return parser.parse_args()


def start_server(logger, model, port):
    if model == 'TCP':
        logger.info('Begin TCP listen %d.' % port)

        SpeedTCPHandler.logger = logger
        with socketserver.TCPServer(('0.0.0.0', port), SpeedTCPHandler) as server:
            server.serve_forever()

    elif model == 'UDP':
        logger.info('Begin UDP listen %d.' % port)

        SpeedUDPHandler.logger = logger
        with socketserver.UDPServer(('0.0.0.0', port), SpeedUDPHandler) as server:
            server.serve_forever()

    else:
        logger.warning('Invalid model: %s.' % model)


def start_client(logger, model, host, port, period):
    # support TCP or UDP mode
    socket_kind = socket.SOCK_STREAM if model == 'TCP' else socket.SOCK_DGRAM
    with socket.socket(family=socket.AF_INET, type=socket_kind) as s:
        client = TCPClient(logger, s) if model == 'TCP' else UDPClient(logger, s)
        client.connect((host, int(port)))
        client.start(period=period)


def main():
    args = get_parser()
    with open(args.config, 'rt') as fp:
        cfg = json.load(fp)

    logger = make_logger(**cfg['log'])

    if args.server:
        start_server(logger, **cfg['server'])

    if args.client:
        start_client(logger, **cfg['client'])


if __name__ == '__main__':
    main()
