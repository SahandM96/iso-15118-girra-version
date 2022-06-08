""" imports in here """
import logging

import zmq

logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")


# make error message template
def make_error_message(error_code: str, error_message: str) -> str:
    return "ERROR: " + error_code + ":" + error_message


def get_evse_id(protocol: str) -> str:
    logger.info("get_evse_id Called")
    if protocol == "DIN_SPEC_70121":
        return "randomDIN"
    return "SM96"

while True:
    message = str(socket.recv()).strip("b'")
    stage, msg = str(message).split(":")
    print(f"stage: {str(stage).strip()} msg: {str(msg).strip()}")
    if stage.strip() == "get_evse_id" or stage == "b\'get_evse_id":
        print("in here")
        print(get_evse_id(msg.strip))
        socket.send_string(get_evse_id(msg.strip()))
    
    print(f"Received request:{0}".format( message))
    socket.send_string(make_error_message("0", "NOT IMPLEMENTED"))

