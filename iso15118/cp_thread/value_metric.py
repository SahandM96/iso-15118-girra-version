import logging

logger = logging.getLogger(__name__)


def value_metric() -> bool:
    try:
        with open('tmp_cp', 'r+') as VALUE:
            if VALUE.read().strip() == 150:
                return True
            VALUE.close()
            return False
    except Exception as exc:
        logger.info(exc)
        raise


def get_cp_value() -> int:
    try:
        with open('tmp_cp', 'r+') as VALUE:
            tmp = int(VALUE.read().strip())
            VALUE.close()
            return tmp
    except Exception as exc:
        logger.info(exc)
        raise


def set_cp_value(param):
    try:
        with open('tmp_cp', 'w+') as VALUE:
            VALUE.write(str(int(param)))
            VALUE.close()
    except Exception as exc:
        logger.info(exc)
        raise
