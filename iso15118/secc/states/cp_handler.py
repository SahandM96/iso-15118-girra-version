""" import os and enums """
import logging


logger = logging.getLogger(__name__)


# class CP(IntEnum):
#     """ just a simple enum for check cp states"""
#     A = 1
#     B = 2
#     C = 3
#     D = 4


async def check_cp() -> int:
    logger.info("Start Checking")
    """ demo function for check state and return CP"""
    with open("/home/sahandm96/cp_adc") as file_cp_adc:
        value = int(file_cp_adc.read())
        return value
