from enum import Enum, IntEnum


class Message_FrameID (IntEnum) :

# The Frame Ids That Controller Sends Into Bus 
    NEWCHARGESESSION_ID      = 0x68001
    INSULATIONTEST_ID        = 0x68002
    PRECHARGE_ID             = 0x68003
    CHARGESTATUSCHANGE_ID    = 0x68004
    CHARGINGLOOP_ID          = 0x68005
    EMERGENCYSTOP_ID         = 0x68006
    CHARGESESSIONFINISHED_ID = 0x68007
    CONTROLLERINPUT_ID       = 0x68008
    CONTROLLERSTATUS_ID      = 0x68009

# The Frame Ids That The Controller Recieves Out Of The Bus 
    POWERMODULESTATUS_ID     = 0x60010
    POWERMODULELIMITS_ID     = 0x60011
    SEQUENCECONTROL_ID       = 0x60012


class Message_Period(float,Enum) :

# If The Message is Not Periodic We Swt The Timeout As "0"
    
    NEWCHARGESESSION_TIMEOUT      = 0.1
    INSULATIONTEST_TIMEOUT        = 0.1
    PRECHARGE_TIMEOUT             = 0.1
    CHARGESTATUSCHANGE_TIMEOUT    = 0
    CHARGINGLOOP_TIMEOUT          = 0.1
    EMERGENCYSTOP_TIMEOUT         = 0.1
    CHARGESESSIONFINISHED_TIMEOUT = 0
    CONTROLLERINPUT_TIMEOUT       = 0.1
    CONTROLLERSTATUS_TIMEOUT      = 0.1

    POWERMODULESTATUS_TIMEOUT     = 0.1
    POWERMODULELIMITS_TIMEOUT     = 0
    SEQUENCECONTROL_TIMEOUT       = 0

class Message_DLC(IntEnum) :
    
    NEWCHARGESESSION_DLC      = 8
    INSULATIONTEST_DLC        = 2
    PRECHARGE_DLC             = 4
    CHARGESTATUSCHANGE_DLC    = 1
    CHARGINGLOOP_DLC          = 5
    EMERGENCYSTOP_DLC         = 1
    CHARGESESSIONFINISHED_DLC = 1
    CONTROLLERINPUT_DLC       = 5
    CONTROLLERSTATUS_DLC      = 1

    POWERMODULESTATUS_DLC     = 8
    POWERMODULELIMITS_DLC     = 8
    SEQUENCECONTROL_DLC       = 3

class Message_DIR(IntEnum) :
    IN = 0
    OUT = 1



class Gira_EVSEControllerStatusType(IntEnum) :

    '''
        Base on Advantics Docs On Page 32 Of Generic EVSE Interface V2

        DOCS :

            Initialising
                Controller’s applications are starting up.
            Waiting_For_PEV
                Controller is idle and ready for a plug-in.
            Negotiating_Connection
                Controller is plugged to a car and the connection is being initialised. Important charge information are
                exchanged.
            Connected_With_Full_Info
                All charge information from the PEV were retrieved and a charge session can be considered to be
                properly open.
            Insulation_Test
                Insulation of the charge cable is being tested.
            Precharge
                Charger is matching its output voltage to the present voltage of the battery.
            Waiting_For_Charge
                PEV is about to begin the actual charging.
            Charging
                Main charging loop going on.
            Ending_Charge
                A normal charge stop condition happenned and the PEV is exiting the charging loop.
            Welding_Detection
                PEV is testing if its contactors are welded.
            Closing_Communication
                PEV can unplug and charger is reinitialising in order to then go back to Waiting_For_PEV.
            CCS_Authorisation_Process
                Special state in CCS to authorise user.
            Not_Available
                Controller has been made unavailable by Sequence_Control.Start_Charge_Authorisation
    '''

    INITIALIZING = 0
    WAITINF_FOR_PEV = 1
    NEGOTIATIONG_CONNECTION = 2
    CONNECTED_WITH_FULL_INFO = 3
    INSULATION_TEST = 4
    PRECHARG = 5
    WAITING_FOR_CHARG = 6
    CHARGING = 7
    ENDING_CHARG = 8
    WELDING_DETECTION = 9
    COLSING_COMMUNICATION = 10
    CCS_AUTHORISATION_PROCESS = 11
    NOT_AVAILABLE = 12



class CommunicationProtocolType (IntEnum) :
    CCS_DIN_70121_2012_V2 = 0
    CCS_ISO_15118_2010_V1 = 1
    CCS_ISO_15118_2013_V2 = 2
    CHAdeMO_V0_9          = 3
    CHAdeMO_V1_TILL_2     = 4
    CHAdeMO_V2            = 5


class PlugAndPinsType(IntEnum) :
    CCS_DC_Core = 0
    CCS_DC_Extended = 1
    CHAdeMO =3


class ChargeStatusType(IntEnum) :
    CHARGE_STOPED = 0
    CHARGE_STARTED = 1




