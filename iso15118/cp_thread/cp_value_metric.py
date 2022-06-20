import logging

logger = logging.getLogger(__name__)


def value_metric() -> bool:
    try:
        if get_cp_value() == 150:
            return True
        return False
    except Exception as exc:
        logger.info(exc)
        raise


def get_cp_value(path="/home/sahandm96/watch_dir/cp_adc") -> int:
    try:
        with open(path, 'r+') as VALUE:
            tmp = int(VALUE.read().strip())
            VALUE.close()
            return tmp
    except Exception as exc:
        logger.info(exc)
        raise


def set_cp_value(param, path="/home/sahandm96/watch_dir/cp_adc"):
    try:
        with open(path, 'w+') as VALUE:
            VALUE.write(str(int(param)))
            VALUE.close()
    except Exception as exc:
        logger.info(exc)
        raise
