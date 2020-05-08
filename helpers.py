import logging


logger = logging.getLogger('logger')
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s - %(levelname)s]: %(message)s')
sh.setFormatter(formatter)
logger.addHandler(sh)


def log(msg):
	logger.info(msg)