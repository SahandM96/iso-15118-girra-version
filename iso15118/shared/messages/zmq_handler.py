import logging
import os
import pickle

import zmq.asyncio

logger = logging.getLogger(__name__)


def message_maker(command: str, payload: bytes) -> bytes:
    return pickle.dumps(
        {
            "command": command,
            "payload": payload
        }
    )


class ZMQHandler:

    def __init__(self) -> None:
        try:
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(os.environ.get('ZMQ_FOR_CP_AND_V2G'))
            self.state = "initializing"
        except Exception as exc:
            logger.error(f"ZMQHandler terminated: {exc}")
            raise

    def get_state(self) -> str:
        return self.state

    def set_state(self, state: str):
        self.state = state

    async def start(self) -> None:
        try:
            res = await self.send_message(state='starting', message=pickle.dumps('connecting'), protocol='v2g_message')
            logger.info(f"Connected to secc {res}")
        except Exception as exc:
            logger.error(f"ZMQHandler terminated: {exc}")
            raise

    async def send_message(self, message: bytes, state: str = "state", protocol: str = 'v2g_message') -> any:
        try:
            if isinstance(message, bytes):
                await self.socket.send(pickle.dumps(
                    {'state': self.get_state(), 'message': message, 'protocol': protocol})
                )
            else:
                await self.socket.send(pickle.dumps(
                    {'state': self.get_state(), 'message': pickle.dumps({'null': message}), 'protocol': protocol}))
                resp: bytes = await self.socket.recv()
                return pickle.loads(resp)
        except Exception as exc:
            logger.error(f"ZMQHandler terminated: {exc}")
            raise
        finally:
            logger.info(f"Sending message to secc on state : {state}")
