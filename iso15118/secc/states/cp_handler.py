""" import os and enums """
import os

from enum import IntEnum

PATH = os.getcwd()


class CP(IntEnum):
    """ just a simple enum for check cp states"""
    A = 1
    B = 2
    C = 3
    D = 4


def check_cp() -> CP:
    """ demo function for check state and return CP"""
    with open(f"{PATH}/cp_adc") as file_cp_adc:
        value = int(file_cp_adc.read())
        if value <= 100 :
            return CP.A
        if value > 100 and value < 200 :
            return CP.B
        if value > 200 :
            return CP.C
        return CP.D
