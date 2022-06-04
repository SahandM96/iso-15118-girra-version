""" import in here """
import logging
import zmq
from threading import Thread

logger = logging.getLogger(__name__)


def zmq_thread():
    while True:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:5555")
        return socket


def zmq_run_server(msg):
    """ run server and send message"""
    socket = zmq_thread()
    socket.send(bytes(msg, "ascii"))
    message = socket.recv()
    print("Received request: %s", message)
