import can
from enums import (
    Message_DIR,
    Message_DLC,
    Message_FrameID,
    Message_Period,
    CommunicationProtocolType,
    Gira_EVSEControllerStatusType,
    PlugAndPinsType,
    ChargeStatusType,

)

from can import (
    Message,
    Bus,
    bus,
    BusABC,
    ModifiableCyclicTaskABC,
)


class CanBaseModel:
    def __init__(self,
                 FrameID: Message_FrameID,
                 DLC: Message_DLC,
                 Period: Message_Period,
                 Direction: bool):
        self.FrameID = FrameID
        self.DLC = DLC
        self.Period = Period
        self.Direction = Direction


class NewChargeSession:
    """
        Base on Advantics Docs On Page 21 Of Generic EVSE Interface V2

        Information about an incoming vehicle.
        Sent periodically from the moment a car is plugged in and all the
        information are known.
        Until power modules send a "System_Enable" with value Allowed

        Arg Comm_Protocol :
            Which Protocol Version Is Used To communicate With Car  => 1Byte

        Arg Plug_pins :
            Hardware Shape Of the Outlet CCS Only = > 1Byte

        Arg EV_Maximum_Voltage :
            Maximum battery voltage "Scale 0.1" In "Volts" => 2Byte

        Arg EV_Maximum_Current :
            Maximum battery current (optional, not all communication protocols give it) "Scale 0.1" In "Amps" =>2Byte

        Arg Battery_Capacity:
            Total battery capacity (optional, not all communication protocols give it) "Scale 2 In "KWh" =>1Byte

        Arg State_of_Charge :
            Battery SoC in percent. => 1Byte

    """

    def __init__(
            self,
            BusHandler: Bus,
            Comm_Protocol: CommunicationProtocolType = None,
            Plug_pins: PlugAndPinsType = None,
            EV_Maximum_Voltage: bytes = 0x00,
            EV_Maximum_Current: bytes = 0x00,
            Battery_Capacity: bytes = 0x00,
            State_of_Charge: bytes = 0x00
    ):

        MsgProp_NewChargeSession = CanBaseModel(
            Message_FrameID.NEWCHARGESESSION_ID,
            Message_DLC.NEWCHARGESESSION_DLC,
            Message_Period.NEWCHARGESESSION_TIMEOUT,
            Message_DIR.IN
        )

        self.BusTask: ModifiableCyclicTaskABC = None
        self.BusHandler: bus = BusHandler
        self.Comm_Protocol = Comm_Protocol
        self.Plug_pins = Plug_pins
        self.EV_Maximum_Voltage = EV_Maximum_Voltage
        self.EV_Maximum_Current = EV_Maximum_Current
        self.Battery_Capacity = Battery_Capacity
        self.State_of_Charge = State_of_Charge
        self.MsgFrame = bytearray(Message_DLC.NEWCHARGESESSION_DLC)
        self.Msg: Message = []

        self._Creat_Frame_()

        self.Msg = Message(
            arbitration_id=MsgProp_NewChargeSession.FrameID,
            dlc=MsgProp_NewChargeSession.DLC,
            is_extended_id=True,
            data=self.MsgFrame
        )

    def _Creat_Frame_(self):

        self.MsgFrame[0] = self.Comm_Protocol
        self.MsgFrame[1] = self.Plug_pins
        self.MsgFrame[2] = (self.EV_Maximum_Voltage & 0xFF)
        self.MsgFrame[3] = ((self.EV_Maximum_Voltage >> 8) & 0xFF)
        self.MsgFrame[4] = (self.EV_Maximum_Current & 0xFF)
        self.MsgFrame[5] = ((self.EV_Maximum_Current >> 8) & 0xFF)
        self.MsgFrame[6] = self.Battery_Capacity
        self.MsgFrame[7] = self.State_of_Charge

    def SendPeriodic(self):
        self.BusTask = self.BusHandler.send_periodic(self.Msg, Message_Period.NEWCHARGESESSION_TIMEOUT)

    def SendOneTime(self):
        self.BusTask = self.BusHandler.send(self.Msg, 0.1)

    def ModifyMessage(
            self,
            Comm_Protocol: CommunicationProtocolType,
            Plug_pins: PlugAndPinsType,
            EV_Maximum_Voltage: bytes,
            EV_Maximum_Current: bytes,
            Battery_Capacity: bytes,
            State_of_Charge: bytes,
    ):
        self.Comm_Protocol = Comm_Protocol
        self.Plug_pins = Plug_pins
        self.EV_Maximum_Voltage = EV_Maximum_Voltage
        self.EV_Maximum_Current = EV_Maximum_Current
        self.Battery_Capacity = Battery_Capacity
        self.State_of_Charge = State_of_Charge

        self.Msg.data[0] = self.Comm_Protocol
        self.Msg.data[1] = self.Plug_pins
        self.Msg.data[2] = (self.EV_Maximum_Voltage & 0xFF)
        self.Msg.data[3] = ((self.EV_Maximum_Voltage >> 8) & 0xFF)
        self.Msg.data[4] = (self.EV_Maximum_Current & 0xFF)
        self.Msg.data[5] = ((self.EV_Maximum_Current >> 8) & 0xFF)
        self.Msg.data[6] = self.Battery_Capacity
        self.Msg.data[7] = self.State_of_Charge
        if isinstance(self.BusTask, ModifiableCyclicTaskABC):
            self.BusTask.modify_data(self.Msg)
            print("Im Modyfiable")
        else:
            print("Im Not Modyfiable")

    def ModifyFrame(self):
        self.BusTask.modify_data(self.Msg)

    def Stop(self):
        self.BusTask.stop()


class InsulationTest:
    '''
        Test the insulation of the cable by applying a voltage from the charger
        Importatnt : The battery is not connected yet
        Power modules report : "Present_Voltage " , "Insulation_Resistance" 
        and the controller decides when the test
        passes or fails


         Arg EV_Maximum_Current :
            
            Voltage to apply .Will be set back to 0 at the end of the test .
            "Scale 0.1" In "Amps" =>2Byte
    '''

    def __init__(
            self,
            BusHandler: Bus,
            Test_Voltage: int,
    ):
        MsgProp_InsulationTest = CanBaseModel(
            Message_FrameID.INSULATIONTEST_ID,
            Message_DLC.INSULATIONTEST_DLC,
            Message_Period.INSULATIONTEST_TIMEOUT,
            Message_DIR.IN
        )
        self.BusTask: ModifiableCyclicTaskABC = None
        self.BusHandler: Bus = BusHandler
        self.TestVoltage = Test_Voltage
        self.MsgFrame = bytearray(Message_DLC.INSULATIONTEST_DLC)
        self._Creat_Frame_()

        self.Msg = Message(
            arbitration_id=MsgProp_InsulationTest.FrameID,
            dlc=MsgProp_InsulationTest.DLC,
            is_extended_id=True,
            data=self.MsgFrame
        )

    def _Creat_Frame_(self):
        self.MsgFrame[0] = (self.TestVoltage & 0xFF)
        self.MsgFrame[1] = ((self.TestVoltage >> 8) & 0xFF)

    def SendPeriodic(self):
        self.BusTask = self.BusHandler.send_periodic(self.Msg, Message_Period.INSULATIONTEST_TIMEOUT)

    def ModifyMessage(
            self,
            Test_Voltage: int,
    ):
        self.Test_Voltage = Test_Voltage

        self.Msg.data[0] = (self.TestVoltage & 0xFF)
        self.Msg.data[1] = ((self.TestVoltage >> 8) & 0xFF)

        self.BusTask.modify_data(self.Msg)

    def ModifyFrame(self):
        self.BusTask.modify_data(self.Msg)

    def Stop(self):
        self.BusTask.stop()


class PreCharge:
    '''
        1)Precharge procedure, with CCS only.

        2)The vehicle decides to consider precharge done when it senses voltage
            on its inlet to be close at 20 V to battery voltage.
        3)Charger is expected to match battery voltage at its output while having no load ,
            apart from the capacitors on the line 
        4) When charging this capacitive load, 
            it shall not output more current than "Maximum_Current"


        Arg Target_Voltage : 
            Voltage to apply "Scale 0.1" In "Volts" =>2Byte

        Arg Maximum_Current : 
            Maximum current allowed by the vehicle (shouldn’t be more than 2A)
            Will be set back to 0 at the end of the precharge procedure
            "Scale 0.1" In "Amps" =>2Byte
    '''

    def __init__(
            self,
            BusHandler: Bus,
            Target_Voltage: int,
            Maximum_Current: int,
    ):
        MsgProp_Precharge = CanBaseModel(
            Message_FrameID.PRECHARGE_ID,
            Message_DLC.PRECHARGE_DLC,
            Message_Period.PRECHARGE_TIMEOUT,
            Message_DIR.IN
        )

        self.BusTask: ModifiableCyclicTaskABC = None
        self.BusHandler: Bus = BusHandler
        self.Target_Voltage = Target_Voltage
        self.Maximum_Current = Maximum_Current
        self.MsgFrame = bytearray(Message_DLC.PRECHARGE_DLC)
        self._Creat_Frame_()

        self.Msg = Message(
            arbitration_id=MsgProp_Precharge.FrameID,
            dlc=MsgProp_Precharge.DLC,
            is_extended_id=True,
            data=self.MsgFrame
        )

    def _Creat_Frame_(self):
        self.MsgFrame[0] = (self.Target_Voltage & 0xFF)
        self.MsgFrame[1] = ((self.Target_Voltage >> 8) & 0xFF)
        self.MsgFrame[2] = (self.Maximum_Current & 0xFF)
        self.MsgFrame[3] = ((self.Maximum_Current >> 8) & 0xFF)

    def SendPeriodic(self):
        self.BusTask = self.BusHandler.send_periodic(self.Msg, Message_Period.INSULATIONTEST_TIMEOUT)

    def ModifyMessage(
            self,
            Test_Voltage: int,
            Maximum_Current: int
    ):
        self.Test_Voltage = Test_Voltage
        self.Maximum_Current = Maximum_Current

        self.Msg.data[0] = (self.Target_Voltage & 0xFF)
        self.Msg.data[1] = ((self.Target_Voltage >> 8) & 0xFF)
        self.Msg.data[2] = (self.Maximum_Current & 0xFF)
        self.Msg.data[3] = ((self.Maximum_Current >> 8) & 0xFF)

        self.BusTask.modify_data(self.Msg)

    def ModifyFrame(self):
        self.BusTask.modify_data(self.Msg)

    def Stop(self):
        self.BusTask.stop()


class ChargeStatusChange:
    '''
        Signal a change in the charging procedure. Sent once only when something change

        Arg Vehicle_Ready_for_Charging :
            Tells when the vehicle intend to start or stop the charge
            If value is "Charge_Started", the power modules must be ready for the charging loop at any moment
            (with CCS it can still be in several hours).
    '''

    def __init__(
            self,
            Vehicle_Ready_for_Charging: ChargeStatusType
    ):
        MsgProp_ChargeStatusChange = CanBaseModel(
            Message_FrameID.CHARGESTATUSCHANGE_ID,
            Message_DLC.CHARGESTATUSCHANGE_DLC,
            Message_Period.CHARGESTATUSCHANGE_TIMEOUT,
            Message_DIR.IN
        )

        self.Vehicle_Ready_for_Charging = Vehicle_Ready_for_Charging
        self.MsgFrame: bytes = []
        self._Creat_Frame_()

        self.Msg = Message(
            arbitration_id=MsgProp_ChargeStatusChange.FrameID,
            dlc=MsgProp_ChargeStatusChange.DLC,
            is_extended_id=True,
            data=self.MsgFrame
        )

    def _Creat_Frame_(self):
        self.MsgFrame = bytearray(Message_DLC.CHARGESTATUSCHANGE_DLC)

        self.MsgFrame[0] = self.Vehicle_Ready_for_Charging


class ChargeLoop:
    '''
        1) Sent during the main charging loop
        2) The vehicle is basically requesting current
            on its inlet to be close at 20 V to battery voltage.
        3) Note that while the request is expressed in both voltage and current,
             it is up to power modules to determine which control mode they should run 
       


        Arg Target_Voltage : 
            Voltage to apply "Scale 0.1" In "Volts" =>2Byte

        Arg Target_Current : 
            Current to provide "Scale 0.1" In "Amps" =>2Byte

        Arg State_of_Charge :
            Battery SoC in percent (informative, do not rely on it).

            
    '''

    def __init__(
            self,
            Target_Voltage,
            Target_Current,
            State_of_Charge,
    ):
        MsgProp_ChargeLoop = CanBaseModel(
            Message_FrameID.CHARGINGLOOP_ID,
            Message_DLC.CHARGINGLOOP_DLC,
            Message_Period.CHARGINGLOOP_TIMEOUT,
            Message_DIR.IN
        )

        self.Target_Voltage = Target_Voltage
        self.Target_Current = Target_Current
        self.State_of_Charge = State_of_Charge
        self.MsgFrame: bytes = []
        self._Creat_Frame_()

        self.Msg = Message(
            arbitration_id=MsgProp_ChargeLoop.FrameID,
            dlc=MsgProp_ChargeLoop.DLC,
            is_extended_id=True,
            data=self.MsgFrame
        )

    def _Creat_Frame_(self):
        self.MsgFrame = bytearray(Message_DLC.CHARGINGLOOP_DLC)

        self.MsgFrame[0] = (self.Target_Voltage & 0xFF)
        self.MsgFrame[1] = ((self.Target_Voltage >> 8) & 0xFF)
        self.MsgFrame[2] = (self.Target_Current & 0xFF)
        self.MsgFrame[3] = ((self.Target_Current >> 8) & 0xFF)
        self.MsgFrame[4] = self.State_of_Charge
