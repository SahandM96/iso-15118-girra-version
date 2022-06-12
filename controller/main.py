""" imports in here """
import logging
import threading
import time
import os
import zmq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")


# make error message template
def make_error_message(error_code: str, error_message: str) -> str:
    return "ERROR: " + error_code + ":" + error_message


def get_evse_id(protocol: str) -> str:
    logger.info("get_evse_id Called")
    if protocol == "DIN":
        return os.environ.get("EVSE_ID_DIN")
    return os.environ.get("EVESE_ID_ISO15188_2")


# handle cp_thead message
def cp_thead_message_handler(message: str) -> str:
    if message == "":
        return "cp_thead:not_set"
    return "cp_thead:" + message


def main():
    while True:
        message: str = socket.recv_string()
        stage, msg = message.split(":")
        print(f"stage: {str(stage).strip()} msg: {str(msg).strip()}")

        if stage == "get_evse_id":
            rsp: str = get_evse_id(str(msg))
            print(f"rsp: {rsp}")
            socket.send_string(f"get_evse_id:{rsp}")
            # time.sleep(0.01)
        elif stage == "cp_thead":
            rsp: str = cp_thead_message_handler(str(msg).strip())
            print(f"rsp: {rsp}")
            socket.send_string(f"cp_thead:{rsp}")
            # time.sleep(0.01)
        else:
            res: str = make_error_message("0", "NOT IMPLEMENTED")
            socket.send_string(res)
        # time.sleep(0.01)


if __name__ == "__main__":
    main()
