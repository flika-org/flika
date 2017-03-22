from logging import getLogger, basicConfig
import os
LOG_DIR = os.path.join(os.path.expanduser("~"), '.FLIKA', 'log')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
LOG_PATH = os.path.join(LOG_DIR, 'FLIKALOG.log')
basicConfig(filename=LOG_PATH)
logger = getLogger("flika")