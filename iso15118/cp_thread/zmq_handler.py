""" import in here """
import pickle
import logging
import zmq
from zmq.asyncio import Context, Poller

url = 'tcp://127.0.0.1:5555'

from iso15118.cp_thread.cp_value_metric import get_cp_value
from threading import Thread

logger = logging.getLogger(__name__)


# set stage on messages
def zmq_thead_message_stage_handler(msg="") -> bytes:
    
    if msg != "":
        return pickle.dumps(f"cp_thead:{msg}")
    else:
        return pickle.dumps(f"cp_thead:not_set")


def zmq_thread():
    while True:
        ctx = Context.instance()
        socket = ctx.socket(zmq.REQ)
        socket.bind("tcp://localhost:5555")
        return socket


def zmq_run_server(msg=""):
    """ run server and send message"""

    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    socket.send(zmq_thead_message_stage_handler(str(get_cp_value())))
    message: str = socket.recv()
    logger.info(message)
    rep :dict = pickle.loads(message)
    stage = rep["stage"]
    message = rep["message"]
    logger.info(f"stage: {stage} message: {message}")

