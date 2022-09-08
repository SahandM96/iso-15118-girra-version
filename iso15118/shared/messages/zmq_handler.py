import logging
import os
import pickle

import zmq.asyncio

logger = logging.getLogger(__name__)


class ZMQHandler:

    def __init__(self) -> None:
        try:
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(os.environ.get('ZMQ_FOR_CP_AND_V2G'))
        except Exception as exc:
            logger.error(f"ZMQHandler terminated: {exc}")
            raise

    async def start(self) -> None:
        try:
            res = await self.send_message(state='starting', message=pickle.dumps('connecting'), protocol='v2g_message')
            logger.info(f"Connected to secc {res}")
        except Exception as exc:
            logger.error(f"ZMQHandler terminated: {exc}")
            raise

    async def send_message(self, state: str, message: bytes, protocol: str = 'v2g_message') -> any:
        try:
            logger.info("Sending message to secc on state : {}".format(state))
            if isinstance(message, bytes):
                await self.socket.send(pickle.dumps({'state': state, 'message': message, 'protocol': protocol}))
            else:
                await self.socket.send(pickle.dumps({'state': state, 'message': pickle.dumps({'null': message}),
                                                     'protocol': protocol}))

            resp: bytes = await self.socket.recv()
            return pickle.loads(resp)
        except Exception as exc:
            logger.error(f"ZMQHandler terminated: {exc}")
            raise
