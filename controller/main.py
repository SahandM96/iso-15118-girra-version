""" imports in here """
import logging
import time
import os
from typing import List, Optional
import pickle
import zmq
from dotenv import load_dotenv

from iso15118.shared.messages.datatypes import EVSEStatus, DCEVSEStatus, PVEVSEMaxPowerLimit, PVEVSEMaxCurrentLimit, \
    PVEVSEMaxVoltageLimit
from iso15118.shared.messages.enums import EnergyTransferModeEnum
from iso15118.shared.messages.iso15118_20.common_messages import ScheduledScheduleExchangeResParams
from iso15118.shared.messages.datatypes import IsolationLevel, DCEVSEStatusCode, EVSENotification

load_dotenv()
logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")


# make error message template
def make_error_message(error_code: str, error_message: str) -> str:
    return "ERROR: " + error_code + ":" + error_message


# handle get_evse_id message
def get_evse_id(protocol: str) -> bytes:
    logger.info("get_evse_id Called")
    if protocol == "DIN":
        return pickle.dumps(os.environ.get("EVSE_ID"))
    else:
        return pickle.dumps(os.environ.get("EVSE_ID"))


# handle get_supported_energy_transfer_modes message
def get_supported_energy_transfer_modes(protocol: str) -> bytes:
    logger.info("get_supported_energy_transfer_modes Called")
    if protocol == "DIN":
        return pickle.dumps([EnergyTransferModeEnum.DC_COMBO_CORE])
    else:
        return pickle.dumps([EnergyTransferModeEnum.DC_EXTENDED])


# handle cp_thead message
def cp_thead_message_handler(message: str) -> bytes:
    if message == "":
        return pickle.dumps("not_set")
    return pickle.dumps(message)


# handle get_evse_status message
def get_scheduled_se_params(message: str) -> Optional[ScheduledScheduleExchangeResParams]:
    pass


# handle is_authorised message
def is_authorised(message: str) -> bytes:
    return pickle.dumps(True)


# handle get_dc_evse_status message
def get_dc_evse_status(param: str) -> bytes:
    jfile = DCEVSEStatus(
        evse_notification=EVSENotification.NONE,
        notification_max_delay=0,
        evse_isolation_status=IsolationLevel.VALID,
        evse_status_code=DCEVSEStatusCode.EVSE_READY,
    )
    return pickle.dumps(jfile, protocol=pickle.HIGHEST_PROTOCOL, fix_imports=True)


def get_evse_max_voltage_limit(param) -> bytes:
    return pickle.dumps(PVEVSEMaxVoltageLimit(multiplier=0, value=600, unit="V"))


def get_evse_max_power_limit(param) -> bytes:
    return pickle.dumps(PVEVSEMaxPowerLimit(multiplier=1, value=1000, unit="W"))


def get_evse_max_current_limit(param) -> bytes:
    return pickle.dumps(PVEVSEMaxCurrentLimit(multiplier=0, value=300, unit="A"))


def start_cable_check(param):
    pass


def pre_charge(param):
    # TODO :
    pass


def set_pre_charge_params(voltage: int, current: int):
    pass


def get_evse_status(param="") -> bytes:
    return pickle.dumps(
        {'notification_max_delay': '0',
         'evse_notification': 'TERMINATE'})


def get_evese_present_voltage(param):
    pass


def main():
    while True:
        message: str = str(socket.recv()).replace("b'", "").replace("'", "")
        stage, msg = message.strip().split(":")
        # print(f"stage: {str(stage)} msg: {str(msg)}")
        if stage == "get_evse_id":
            rsp: bytes = get_evse_id(str(msg))
            print(f"get_evse_id: {rsp}")
            socket.send(rsp)
            # time.sleep(0.01)
        elif stage == "cp_thead":
            rsp: bytes = cp_thead_message_handler(str(msg))
            print(f"cp_thead_message_handler: {rsp}")
            socket.send(rsp)
            # time.sleep(0.01)
        elif stage == "get_supported_energy_transfer_modes":
            rsp: bytes = get_supported_energy_transfer_modes(str(msg))
            print(f"get_supported_energy_transfer_modes:{rsp}")
            socket.send(rsp)
            # time.sleep(0.01)
        elif stage == "is_authorised":
            rsp: bytes = is_authorised(message)
            print(f"is_authorised:{rsp}")
            socket.send(rsp)
            # time.sleep(0.01)
        elif stage == "get_evse_status":
            rsp: bytes = get_evse_status(str(msg))
            print(f"get_evse_status:{rsp}")
            socket.send(rsp)
        elif stage == "get_dc_evse_status":
            rsp: bytes = get_dc_evse_status(str(msg))
            print(f"get_dc_evse_status:{rsp}")
            socket.send(rsp)
        elif stage == "get_evse_max_power_limit":
            rsp: bytes = get_evse_max_power_limit(str(msg))
            print(f"get_evse_max_power_limit:{rsp}")
            socket.send(rsp)
        elif stage == "get_evse_max_voltage_limit":
            rsp: bytes = get_evse_max_voltage_limit(str(msg))
            print(f"get_evse_max_voltage_limit:{rsp}")
            socket.send(rsp)
        elif stage == "get_evse_max_current_limit":
            rsp: bytes = get_evse_max_current_limit(str(msg))
            print(f"get_evse_max_current_limit:{rsp}")
            socket.send(rsp)
        else:
            res: bytes = pickle.dumps(make_error_message("0", "NOT IMPLEMENTED"))
            socket.send(res)
        # time.sleep(0.01)


if __name__ == "__main__":
    main()
