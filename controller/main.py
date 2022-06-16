""" imports in here """
import logging
import time
import os
from multiprocessing.pool import TERMINATE
from typing import List, Optional

import zmq
from dotenv import load_dotenv

from iso15118.shared.messages.datatypes import EVSEStatus, DCEVSEStatus
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


def get_evse_id(protocol: str) -> str:
    logger.info("get_evse_id Called")
    if protocol == "DIN":
        return os.environ.get("EVSE_ID")
    else:
        return os.environ.get("EVSE_ID")


def get_supported_energy_transfer_modes(protocol: str) -> EnergyTransferModeEnum:
    logger.info("get_supported_energy_transfer_modes Called")
    if protocol == "DIN":
        dc_extended = EnergyTransferModeEnum.DC_COMBO_CORE
        return dc_extended
    else:
        dc_extended = EnergyTransferModeEnum.DC_EXTENDED
        return dc_extended


# handle cp_thead message
def cp_thead_message_handler(message: str) -> str:
    if message == "":
        return "cp_thead:not_set"
    return "cp_thead:" + message


def get_scheduled_se_params(message: str) -> Optional[ScheduledScheduleExchangeResParams]:
    pass


def is_authorised(message: str) -> bool:
    return True


def get_dc_evse_status(param: str) -> dict[str, any]:
    return {
        'evse_notification': EVSENotification.NONE,
        'notification_max_delay': 0,
        'evse_isolation_status': IsolationLevel.VALID,
        'evse_status_code': DCEVSEStatusCode.EVSE_READY,
    }


def start_cable_check(param):
    pass


def pre_charge(param):
    # TODO :
    pass


def set_pre_charge_params(voltage: int, current: int):
    pass


def get_evse_status(param="") -> EVSEStatus:
    return EVSEStatus(notification_max_delay=0, evse_notification=TERMINATE)


def get_evese_present_voltage(param):
    pass


def main():
    while True:
        message: str = socket.recv_string()
        stage, msg = message.split(":")
        print(f"stage: {str(stage).strip()} msg: {str(msg).strip()}")

        if stage == "get_evse_id":
            rsp: str = get_evse_id(str(msg))
            print(f"get_evse_id: {rsp}")
            socket.send_string(f"get_evse_id:{rsp}")
            # time.sleep(0.01)
        elif stage == "cp_thead":
            rsp: str = cp_thead_message_handler(str(msg).strip())
            print(f"cp_thead_message_handler: {rsp}")
            socket.send_string(f"cp_thead:{rsp}")
            # time.sleep(0.01)
        elif stage == "get_supported_energy_transfer_modes":
            rsp: EnergyTransferModeEnum = get_supported_energy_transfer_modes(str(msg).strip())
            print(f"get_supported_energy_transfer_modes: {rsp}")
            socket.send_string(f"get_supported_energy_transfer_modes:{rsp}")
            # time.sleep(0.01)
        elif stage == "is_authorised":
            rsp: bool = is_authorised(message)
            print(f"is_authorised: {rsp}")
            socket.send_string(f"is_authorised:{rsp}")
            # time.sleep(0.01)
        elif stage == "get_evse_status":
            rsp: EVSEStatus = get_evse_status(str(msg).strip())
            print(f"get_evse_status: {rsp}")
            socket.send_string(f"get_dc_evse_status:{rsp}")
        elif stage == "get_dc_evse_status":
            rsp: dict = get_dc_evse_status(str(msg).strip())
            print(f"get_dc_evse_status: {rsp}")
            socket.send_string(f"get_dc_evse_status:{rsp}")
        else:
            res: str = make_error_message("0", "NOT IMPLEMENTED")
            socket.send_string(res)
        # time.sleep(0.01)


if __name__ == "__main__":
    main()
