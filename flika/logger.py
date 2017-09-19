from logging import *
import os

def get_log_file():
    LOG_DIR = os.path.join(os.path.expanduser("~"), '.FLIKA', 'log')
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    existing_files = os.listdir(LOG_DIR)
    existing_files = [f for f in existing_files if 'flikalog.' in f]
    if len(existing_files) == 0:
        log_idx = 0
    else:
        log_idx = existing_files[-1].split('.')[1]
        try:
            log_idx = int(log_idx) + 1
        except ValueError:
            log_idx = 0
    LOG_FILE = os.path.join(LOG_DIR, 'flikalog.{}.log'.format(log_idx))
    return LOG_FILE

LOG_FILE = get_log_file()
FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
basicConfig(filename=LOG_FILE, format=FORMAT)
logger = getLogger("flika")
logger.setLevel(DEBUG)
handler = StreamHandler()
handler.setLevel(DEBUG)
formatter = Formatter(FORMAT)
handler.setFormatter(formatter)
logger.addHandler(handler)
