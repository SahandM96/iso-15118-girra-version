""" import in here """
import logging
import zmq
from iso15118.cp_thread.value_metric import get_cp_value
from threading import Thread

logger = logging.getLogger(__name__)


# set stage on messages
def zmq_thead_message_stage_handler(msg="") -> str:
    if msg != "":
        return f"cp_thead:{msg}"
    else:
        return f"cp_thead:not_set"


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
    # socket.identity = u"cp_handler_to_controller".encode("ascii")
    socket.connect("tcp://localhost:5555")

    socket.send_string(zmq_thead_message_stage_handler(str(get_cp_value())))

    message: str = socket.recv_string()
    stage, message = message.split(":")

    print("Received request: %s", message)
