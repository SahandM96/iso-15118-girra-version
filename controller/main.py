""" imports in here """
import logging
import os
from typing import Optional
import pickle
import zmq
from dotenv import load_dotenv
import can

from controller.Messages import PreCharge, ChargeLoop, InsulationTest
from iso15118.shared.messages.datatypes import EVSEStatus, DCEVSEStatus, PVEVSEMaxPowerLimit, PVEVSEMaxCurrentLimit, \
    PVEVSEMaxVoltageLimit, PVEVSEPresentCurrent, PVEVSEPresentVoltage, PVEVSEPeakCurrentRipple, PVEVSEMinVoltageLimit, \
    PVEVSEMinCurrentLimit, DCEVSEChargeParameter, PVEVTargetVoltage, PVEVTargetCurrent
from iso15118.shared.messages.enums import EnergyTransferModeEnum, Contactor
from iso15118.shared.messages.iso15118_20.common_messages import ScheduledScheduleExchangeResParams
from iso15118.shared.messages.datatypes import IsolationLevel, DCEVSEStatusCode, EVSENotification
from iso15118.shared.messages.iso15118_20.common_types import RationalNumber
from iso15118.shared.messages.iso15118_20.dc import DCChargeParameterDiscoveryResParams, \
    BPTDCChargeParameterDiscoveryResParams

import utils

load_dotenv()
logger = logging.getLogger(__name__)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind(os.environ.get('ZMQ_FOR_CP_AND_V2G'))
InterfaceBus = can.Bus(
    interface='socketcan',
    channel='vcan0'
)


def open_contactor(param: dict) -> bytes:
    logger.info("Contactor is {}".format(Contactor.OPENED))
    pickle.dump(Contactor.OPENED, open(os.environ.get('CONTACTOR_STATUS_CODE'), 'wb'))
    return pickle.dumps(Contactor.OPENED, fix_imports=True)


def close_contactor(param: dict) -> bytes:
    logger.info("Contactor is {}".format(Contactor.CLOSED))
    pickle.dump(Contactor.CLOSED, open(os.environ.get('CONTACTOR_STATUS_CODE'), 'wb'))
    return pickle.dumps(Contactor.CLOSED, fix_imports=True)


def get_contactor_state(param: dict) -> bytes:
    status = pickle.load(open(os.environ.get('CONTACTOR_STATUS_CODE'), 'rb'))
    # TODO: change it to be really status
    if status == Contactor.CLOSED:
        return pickle.dumps(Contactor.CLOSED, fix_imports=True)
    return pickle.dumps(Contactor.OPENED, fix_imports=True)
    # return pickle.dumps(Contactor.CLOSED)


# send charge command
def send_charging_command(param: dict) -> None:
    print(param.get('soc'))
    soc = param.get('soc')
    vr, cr = utils.decode_voltage_and_current(param)
    print(f"Bus send Voltage: {vr} , Current: {cr} SOC: {soc}")
    # pc = ChargeLoop(InterfaceBus, vr, cr, soc)


# make error message template
def make_error_message(error_code: str, error_message: str) -> str:
    return "ERROR: " + error_code + ":" + error_message


# handle get_evse_id message
def get_evse_id(protocol: dict) -> bytes:
    logger.info("get_evse_id Called")
    if protocol.get('protocol') == "DIN":
        return pickle.dumps(os.environ.get("EVSE_ID"))
    else:
        return pickle.dumps(os.environ.get("EVSE_ID"))


# handle get_supported_energy_transfer_modes message
def get_supported_energy_transfer_modes(protocol: dict) -> bytes:
    logger.info("get_supported_energy_transfer_modes Called")
    if protocol.get('protocol') == "DIN":
        return pickle.dumps([EnergyTransferModeEnum.DC_COMBO_CORE])
    else:
        return pickle.dumps([EnergyTransferModeEnum.DC_EXTENDED])


# handle cp_thead message
def cp_thead_message_handler(message: dict) -> bytes:
    if message == "":
        return pickle.dumps("not_set")
    return pickle.dumps(message)


# TODO: implement this
def get_scheduled_se_params(message: dict) -> Optional[ScheduledScheduleExchangeResParams]:
    pass


# handle is_authorised message
def is_authorised(message: dict) -> bytes:
    return pickle.dumps(True)


# handle get_dc_evse_status message
def get_dc_evse_status(param: dict) -> bytes:
    if get_state({'null': 'null'}):
        return pickle.dumps(DCEVSEStatus(
            evse_notification=EVSENotification.NONE,
            notification_max_delay=0,
            evse_isolation_status=IsolationLevel.VALID,
            evse_status_code=DCEVSEStatusCode.EVSE_READY,
        ))
    return pickle.dumps(DCEVSEStatus(
        evse_notification=EVSENotification.NONE,
        notification_max_delay=0,
        evse_isolation_status=IsolationLevel.VALID,
        evse_status_code=DCEVSEStatusCode.EVSE_READY,
    ))


def get_evse_max_voltage_limit(param: dict) -> bytes:
    return pickle.dumps(PVEVSEMaxVoltageLimit(multiplier=0, value=600, unit="V"))


def get_evse_max_power_limit(param: dict) -> bytes:
    return pickle.dumps(PVEVSEMaxPowerLimit(multiplier=1, value=1000, unit="W"))


def get_evse_max_current_limit(param: dict) -> bytes:
    return pickle.dumps(PVEVSEMaxCurrentLimit(multiplier=0, value=300, unit="A"))


# TODO: implement this
def start_cable_check(param: dict):
    tv = os.environ.get("TEST_VOLTAGE")
    # pc = InsulationTest(InterfaceBus,tv)
    print(f'Bus send Test Voltage: {tv}')
    # pc.SendPeriodic()


def set_precharge(param: dict):
    vr, cr = utils.decode_voltage_and_current(param)
    print('Bus send Voltage: {vr} , Current: {cr}'.format(vr=vr, cr=cr))
    # pc = PreCharge(InterfaceBus, vr, cr)
    # pc.SendPeriodic()


def get_evse_status(param: dict) -> bytes:
    return pickle.dumps(
        {'notification_max_delay': '0',
         'evse_notification': 'TERMINATE'})


# TODO: implement this
def get_evese_present_voltage(param: dict):
    pass


def is_evse_power_limit_achieved(param: dict) -> bytes:
    return pickle.dumps(False)


def is_evse_voltage_limit_achieved(param: dict) -> bytes:
    return pickle.dumps(False)


def is_evse_current_limit_achieved(param: dict) -> bytes:
    return pickle.dumps(False)


def get_evse_present_current(param: dict) -> bytes:
    return pickle.dumps(PVEVSEPresentCurrent(multiplier=0, value=1, unit="A"))


def get_evse_present_voltage(param: dict) -> bytes:
    return pickle.dumps(PVEVSEPresentVoltage(multiplier=0, value=230, unit="V"))


def get_dc_evse_charge_parameter(param: dict) -> bytes:
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
def get_dc_charge_params_v20(param: dict) -> bytes:
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
def get_dc_bpt_charge_params_v20(param: dict) -> bytes:
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


def get_state(param: dict) -> None:
    print('state is : {}'.format(param.get('state')))


def main():
    while True:
        message: dict = pickle.loads(socket.recv())
        stage = message.get('stage')
        message: bytes = message.get('messages')
        if stage == "get_evse_id":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_evse_id(msg)
            print(f"get_evse_id:  Called")
            socket.send(rsp)
        elif stage == "cp_thead":
            msg: dict = pickle.loads(message)
            rsp: bytes = cp_thead_message_handler(msg)
            print(f"cp_thead_message_handler:  Called")
            socket.send(rsp)
        elif stage == "get_supported_energy_transfer_modes":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_supported_energy_transfer_modes(msg)
            print(f"get_supported_energy_transfer_modes: Called")
            socket.send(rsp)
        elif stage == "is_authorised":
            message: dict = pickle.loads(message)
            rsp: bytes = is_authorised(message)
            print(f"is_authorised: Called")
            socket.send(rsp)
        elif stage == "get_evse_status":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_evse_status(msg)
            print(f"get_evse_status: Called")
            socket.send(rsp)
        elif stage == "get_dc_evse_status":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_dc_evse_status(msg)
            print(f"get_dc_evse_status: Called")
            socket.send(rsp)
        elif stage == "get_evse_max_power_limit":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_evse_max_power_limit(msg)
            print(f"get_evse_max_power_limit: Called")
            socket.send(rsp)
        elif stage == "get_evse_max_voltage_limit":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_evse_max_voltage_limit(msg)
            print(f"get_evse_max_voltage_limit: Called")
            socket.send(rsp)
        elif stage == "get_evse_max_current_limit":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_evse_max_current_limit(msg)
            print(f"get_evse_max_current_limit: Called")
            socket.send(rsp)
        elif stage == "is_evse_power_limit_achieved":
            msg: dict = pickle.loads(message)
            rsp: bytes = is_evse_power_limit_achieved(msg)
            print(f"is_evse_power_limit_achieved: Called")
            socket.send(rsp)
        elif stage == "is_evse_voltage_limit_achieved":
            msg: dict = pickle.loads(message)
            rsp: bytes = is_evse_voltage_limit_achieved(msg)
            print(f"is_evse_voltage_limit_achieved: Called")
            socket.send(rsp)
        elif stage == "is_evse_current_limit_achieved":
            msg: dict = pickle.loads(message)
            rsp: bytes = is_evse_current_limit_achieved(msg)
            print(f"is_evse_current_limit_achieved: Called")
            socket.send(rsp)
        elif stage == "start_cable_check":
            msg: dict = pickle.loads(message)
            _: bytes = start_cable_check(msg)
            socket.send(b"start_cable_check: Called")
        elif stage == "get_evse_present_current":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_evse_present_current(msg)
            print(f"get_evse_present_current: Called")
            socket.send(rsp)
        elif stage == "get_evse_present_voltage":
            msg: dict = pickle.loads(message)
            rsp: bytes = get_evse_present_voltage(msg)
            print(f"get_evse_present_voltage: Called")
            socket.send(rsp)
        elif stage == 'get_dc_evse_charge_parameter':
            msg: dict = pickle.loads(message)
            rsp: bytes = get_dc_evse_charge_parameter(msg)
            print(f"get_dc_evse_charge_parameter: Called")
            socket.send(rsp)
        elif stage == 'get_dc_charge_params_v20':
            msg: dict = pickle.loads(message)
            rsp: bytes = get_dc_charge_params_v20(msg)
            print(f"get_dc_charge_params_v20: Called")
            socket.send(rsp)
        elif stage == 'get_dc_bpt_charge_params_v20':
            msg: dict = pickle.loads(message)
            rsp: bytes = get_dc_bpt_charge_params_v20(msg)
            print(f"get_dc_bpt_charge_params_v20: Called")
            socket.send(rsp)
        elif stage == 'close_contactor':
            msg: dict = pickle.loads(message)
            rsp: bytes = close_contactor(msg)
            print(f"close_contactor: {pickle.loads(rsp)}")
            socket.send(rsp)
        elif stage == 'open_contactor':
            msg: dict = pickle.loads(message)
            rsp: bytes = open_contactor(msg)
            print(f"open_contactor: {pickle.loads(rsp)}")
            socket.send(rsp)
        elif stage == 'get_contactor_state':
            msg: dict = pickle.loads(message)
            rsp: bytes = get_contactor_state(msg)
            print(f"get_contactor_state: {pickle.loads(rsp)}")
            socket.send(rsp)
        elif stage == 'set_precharge':
            msg: dict = pickle.loads(message)
            set_precharge(msg)
            print(f"set_precharge: Called")
            socket.send(bytes('ok', 'utf-8'))
        elif stage == 'send_charging_command':
            msg: dict = pickle.loads(message)
            send_charging_command(msg)
            print(f"send_charging_command: Called")
            socket.send(bytes('ok', 'utf-8'))
        elif stage == 'get_state':
            msg: dict = pickle.loads(message)
            get_state(msg)
            print(f"get_status: {msg.get('state')}")
            socket.send(bytes('ok', 'utf-8'))
        else:
            res: bytes = pickle.dumps(make_error_message("0", "NOT IMPLEMENTED"))
            socket.send(res)
        # time.sleep(0.01)


if __name__ == "__main__":
    main()
