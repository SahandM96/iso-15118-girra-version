""" import in here """
import logging
import zmq
from iso15118.cp_thread.value_metric import get_cp_value
from threading import Thread

logger = logging.getLogger(__name__)


def zmq_thread():
    while True:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:5555")
        return socket


def zmq_run_server(msg=""):
    """ run server and send message"""

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    socket.send(bytes(str(get_cp_value()), "ascii"))
    message = socket.recv()
    print("Received request: %s", message)
