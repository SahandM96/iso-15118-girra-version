""" imports in here """
import logging
import time
import os
from typing import List, Optional
import pickle
import zmq
from dotenv import load_dotenv
import can

from iso15118.shared.messages.datatypes import EVSEStatus, DCEVSEStatus, PVEVSEMaxPowerLimit, PVEVSEMaxCurrentLimit, \
    PVEVSEMaxVoltageLimit, PVEVSEPresentCurrent, PVEVSEPresentVoltage, PVEVSEPeakCurrentRipple, PVEVSEMinVoltageLimit, \
    PVEVSEMinCurrentLimit, DCEVSEChargeParameter
from iso15118.shared.messages.enums import EnergyTransferModeEnum, Contactor
from iso15118.shared.messages.iso15118_20.common_messages import ScheduledScheduleExchangeResParams
from iso15118.shared.messages.datatypes import IsolationLevel, DCEVSEStatusCode, EVSENotification
from iso15118.shared.messages.iso15118_20.common_types import RationalNumber
from iso15118.shared.messages.iso15118_20.dc import DCChargeParameterDiscoveryResParams, \
    BPTDCChargeParameterDiscoveryResParams

load_dotenv()
logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")


class StateOfContactor:

    def __init__(self, contactor: Contactor):
        self.contactor = contactor.OPENED




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


# TODO: implement this
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

# TODO: implement this
def start_cable_check(param):
    pass

# TODO: implement this
def pre_charge(param):
    # TODO :
    pass



# TODO: implement this
def set_pre_charge_params(voltage: int, current: int):
    pass


def get_evse_status(param="") -> bytes:
    return pickle.dumps(
        {'notification_max_delay': '0',
         'evse_notification': 'TERMINATE'})


# TODO: implement this
def get_evese_present_voltage(param):
    pass


def is_evse_power_limit_achieved(param) -> bytes:
    return pickle.dumps(True)


def is_evse_voltage_limit_achieved(param) -> bytes:
    return pickle.dumps(True)


def is_evse_current_limit_achieved(param) -> bytes:
    return pickle.dumps(True)


def get_evse_present_current(param) -> bytes:
    return pickle.dumps(PVEVSEPresentCurrent(multiplier=0, value=1, unit="A"))


def get_evse_present_voltage(param) -> bytes:
    return pickle.dumps(PVEVSEPresentVoltage(multiplier=0, value=230, unit="V"))


def get_dc_evse_charge_parameter(param) -> bytes:
    return pickle.dumps(DCEVSEChargeParameter(
        dc_evse_status=DCEVSEStatus(
            notification_max_delay=100,
            evse_notification=EVSENotification.NONE,
            evse_isolation_status=IsolationLevel.VALID,
            evse_status_code=DCEVSEStatusCode.EVSE_READY,
        ),
        evse_maximum_power_limit=PVEVSEMaxPowerLimit(
            multiplier=1, value=230, unit="W"
        ),
        evse_maximum_current_limit=PVEVSEMaxCurrentLimit(
            multiplier=1, value=4, unit="A"
        ),
        evse_maximum_voltage_limit=PVEVSEMaxVoltageLimit(
            multiplier=1, value=4, unit="V"
        ),
        evse_minimum_current_limit=PVEVSEMinCurrentLimit(
            multiplier=1, value=2, unit="A"
        ),
        evse_minimum_voltage_limit=PVEVSEMinVoltageLimit(
            multiplier=1, value=4, unit="V"
        ),
        evse_peak_current_ripple=PVEVSEPeakCurrentRipple(
            multiplier=1, value=4, unit="A"
        ),
    ))


# handle get_dc_evse_charge_parameter message
def get_dc_charge_params_v20(param) -> bytes:
    return pickle.dumps(DCChargeParameterDiscoveryResParams(
        evse_max_charge_power=RationalNumber(exponent=3, value=300),
        evse_min_charge_power=RationalNumber(exponent=0, value=100),
        evse_max_charge_current=RationalNumber(exponent=0, value=300),
        evse_min_charge_current=RationalNumber(exponent=0, value=10),
        evse_max_voltage=RationalNumber(exponent=0, value=1000),
        evse_min_voltage=RationalNumber(exponent=0, value=10),
        evse_power_ramp_limit=RationalNumber(exponent=0, value=10),
    )
    )


# handle get_dc_bpt_charge_params_v20 message
def get_dc_bpt_charge_params_v20(param) -> bytes:
    return pickle.dumps(BPTDCChargeParameterDiscoveryResParams(
        evse_max_charge_power=RationalNumber(exponent=3, value=300),
        evse_min_charge_power=RationalNumber(exponent=0, value=100),
        evse_max_charge_current=RationalNumber(exponent=0, value=300),
        evse_min_charge_current=RationalNumber(exponent=0, value=10),
        evse_max_voltage=RationalNumber(exponent=0, value=1000),
        evse_min_voltage=RationalNumber(exponent=0, value=10),
        evse_max_discharge_power=RationalNumber(exponent=3, value=11),
        evse_min_discharge_power=RationalNumber(exponent=3, value=1),
        evse_max_discharge_current=RationalNumber(exponent=0, value=11),
        evse_min_discharge_current=RationalNumber(exponent=0, value=0),
    )
    )


# handle opening contactor message
def open_contactor(param) -> bytes:

    return pickle.dumps(Contactor.OPENED)


def close_contactor(param):
    return pickle.dumps(Contactor.OPENED)


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
        elif stage == "is_evse_power_limit_achieved":
            rsp: bytes = is_evse_power_limit_achieved(str(msg))
            print(f"is_evse_power_limit_achieved:{rsp}")
            socket.send(rsp)
        elif stage == "is_evse_voltage_limit_achieved":
            rsp: bytes = is_evse_voltage_limit_achieved(str(msg))
            print(f"is_evse_voltage_limit_achieved:{rsp}")
            socket.send(rsp)
        elif stage == "is_evse_current_limit_achieved":
            rsp: bytes = is_evse_current_limit_achieved(str(msg))
            print(f"is_evse_current_limit_achieved:{rsp}")
            socket.send(rsp)
        elif stage == "start_cable_check":
            rsp: bytes = start_cable_check(str(msg))
            print(f"start_cable_check:{rsp}")
            socket.send(rsp)
        elif stage == "get_evse_present_current":
            rsp: bytes = get_evse_present_current(str(msg))
            print(f"get_evse_present_current:{rsp}")
            socket.send(rsp)
        elif stage == "get_evse_present_voltage":
            rsp: bytes = get_evse_present_voltage(str(msg))
            print(f"get_evse_present_voltage:{rsp}")
            socket.send(rsp)
        elif stage == 'get_dc_evse_charge_parameter':
            rsp: bytes = get_dc_evse_charge_parameter(str(msg))
            print(f"get_dc_evse_charge_parameter:{rsp}")
            socket.send(rsp)
        elif stage == 'get_dc_charge_params_v20':
            rsp: bytes = get_dc_charge_params_v20(str(msg))
            print(f"get_dc_charge_params_v20:{rsp}")
            socket.send(rsp)
        elif stage == 'get_dc_bpt_charge_params_v20':
            rsp: bytes = get_dc_bpt_charge_params_v20(str(msg))
            print(f"get_dc_bpt_charge_params_v20:{rsp}")
            socket.send(rsp)
        elif stage == 'open_contactor':
            rsp: bytes = open_contactor(str(msg))
            print(f"open_contactor:{rsp}")
            socket.send(rsp)
        elif stage == 'close_contactor':
            rsp: bytes = close_contactor(str(msg))
            print(f"close_contactor:{rsp}")
            socket.send(rsp)
        else:
            res: bytes = pickle.dumps(make_error_message("0", "NOT IMPLEMENTED"))
            socket.send(res)
        # time.sleep(0.01)


if __name__ == "__main__":
    main()
