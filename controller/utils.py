from iso15118.shared.messages.datatypes import PVEVTargetCurrent, PVEVTargetVoltage




def decode_voltage_and_current(param: dict) :
    voltage: PVEVTargetVoltage = param.get('voltage')
    current: PVEVTargetCurrent = param.get('current')

    vr: int = voltage.value * 10 ^ voltage.multiplier
    cr: int = current.value * 10 ^ current.multiplier
    # return Voltage and Current
    return vr, cr
