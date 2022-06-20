from enum import IntEnum
import pickle
import os

class Contactor(IntEnum):
    OPENED = 1
    CLOSED = 2

contactor_status_path=os.environ.get('CONTACTOR_STATUS_CODE')

def open_contactor(param: dict) -> bytes:
    contactor = open(contactor_status_path, 'w')

    contactor.write("1")
    contactor.close()
    return pickle.dumps(Contactor.OPENED)


def close_contactor(param: dict):
    contactor = open(contactor_status_path, 'w')
    contactor.write("0")
    contactor.close()
    return pickle.dumps(Contactor.OPENED)

def get_contactor_state(param: dict) -> bytes:
    contactor = open(contactor_status_path, 'r')
    status = contactor.read()
    contactor.close()
    if status == 1:
        return pickle.dumps(Contactor.CLOSED)
    return pickle.dumps(Contactor.OPENED)

