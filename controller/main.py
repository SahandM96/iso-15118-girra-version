import logging
import time

import zmq

try:
    while True:
        logger = logging.getLogger(__name__)
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://*:5555")

        message = socket.recv()
        logger.info("Received request: %s" % message)

        #  Do some 'work'
        time.sleep(1)

        #  Send reply back to client
        socket.send(b"World")
finally:
    socket.close()

