import pickle
import time

import can
import zmq

from Messages import (
    CanBaseModel,
    NewChargeSession,
    InsulationTest,
    PreCharge,
)


if __name__ == "__main__":
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5556")
    i = 0

    message: dict = pickle.loads(socket.recv())
    print(message)

    if message.get('state') == 'precharge':

        while True:
            print("Hello")
            pc.Stop()
            break
            # ncs.Stop()
            # sleep(3)
            # ncs.SendPeriodic()
            # i+=1
            # EVSEControllerStatus_ChangeState(Task, i)
            # if i==13 :
            # i = 0

            # ncs.ModifyMessage(
            #     CommunicationProtocolType.CCS_ISO_15118_2013_V2 ,
            #     PlugAndPinsType.CCS_DC_Extended,
            #     0x0011,
            #     0x001D,
            #     50,
            #     17
            # )
            # sleep(2)
            # ncs.SendOneTime()

            # sleep(5)
            # # ncs.Stop()
            # # sleep(2)
            # ncs.ModifyMessage(
            #     CommunicationProtocolType.CCS_ISO_15118_2010_V1 ,
            #     PlugAndPinsType.CCS_DC_Extended,
            #     0x0066,
            #     0x0077,
            #     33,
            #     6
            # )
            # ncs.SendPeriodic()
            # sleep(5)
            # ncs.ModifyMessage(
            #     CommunicationProtocolType.CCS_ISO_15118_2013_V2 ,
            #     PlugAndPinsType.CCS_DC_Extended,
            #     0x0011,
            #     0x001D,
            #     50,
            #     17
            # )

            # sleep(2)
