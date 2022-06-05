import asyncio
import logging

from iso15118.secc import SECCHandler
from iso15118.secc.controller.simulator import SimEVSEController
from iso15118.shared.exificient_exi_codec import ExificientEXICodec
from iso15118.cp_thread.main import run_cp_thread
import threading
logger = logging.getLogger(__name__)


async def main():
    """
    Entrypoint function that starts the ISO 15118 code running on
    the SECC (Supply Equipment Communication Controller)
    """
    sim_evse_controller = await SimEVSEController.create()
    # await run_cp_thread()
    await SECCHandler(
        exi_codec=ExificientEXICodec(), evse_controller=sim_evse_controller
    ).start()


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.debug("SECC program terminated manually")


if __name__ == "__main__":
    t1 = threading.Thread(target=run)
    t2 = threading.Thread(target=run_cp_thread)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
