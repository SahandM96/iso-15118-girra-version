""" import in here """
import logging
import zmq

logger = logging.getLogger(__name__)


def run_server(msg):
    """ run server and send message"""
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    socket.send(bytes(msg,"ascii"))
    message = socket.recv()
    print("Received request: %s" , message)
