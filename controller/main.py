""" imports in here """
import logging

import zmq

logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
try:
    while True:
        socket.bind("tcp://*:5555")

        message = socket.recv()
        print("Received request: %s", message)

        #  Send reply back to client
        socket.send(b"World")
finally:
    socket.close()
