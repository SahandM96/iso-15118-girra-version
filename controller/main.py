""" imports in here """
import logging
import threading
import time

import zmq

logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.ROUTER)
socket.bind("tcp://*:5555")


# make error message template
def make_error_message(error_code: str, error_message: str) -> str:
    return "ERROR: " + error_code + ":" + error_message


def get_evse_id(protocol: str) -> str:
    logger.info("get_evse_id Called")
    if protocol == "DIN_SPEC_70121":
        return "randomDIN"
    return "SM96"


# handle cp_thead message
def cp_thead_message_handler(message: str) -> str:
    if message == "":
        return "cp_thead:not_set"
    return "cp_thead:" + message


def main():
    while True:
        message: str = str(socket.recv_multipart()[1]).replace("b'", "").replace("'", "")
        print(message)
        stage, msg = message.split(":")
        print(f"stage: {str(stage).strip()} msg: {str(msg).strip()}")

        if stage == "get_evse_id":
            rsp: str = get_evse_id(str(msg))
            print(f"rsp: {rsp}")
            socket.send(b"get_evse_id:" + rsp.encode())
            time.sleep(0.01)

        if stage == "cp_thead":
            rsp: str = cp_thead_message_handler(str(msg).strip())
            print(f"rsp: {rsp}")
            socket.send(b"cp_thead:" + rsp.encode())
            time.sleep(0.01)

        res: str = make_error_message("0", "NOT IMPLEMENTED")
        socket.send(res.encode())
        time.sleep(0.01)


if __name__ == "__main__":
    t1 = threading.Thread(target=main)
    t1.start()
    t1.join()
