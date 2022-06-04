""" imports in here """
import logging

import zmq

logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")
while True:
    message = socket.recv()
    logger.info("Received request: %s", message)
    print("Received request: %s", message)
    socket.send(b"controller wait for new message")

