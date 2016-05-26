from PyInstaller import log as logging 
from PyInstaller import compat
from os import listdir

## import all the mkl files for numpy
mkldir = compat.base_prefix + "/Lib/site-packages/numpy/core" 
logger = logging.getLogger(__name__)
logger.info("MKL installed as part of numpy, importing that!")
binaries = [(mkldir + "/" + mkl, '.') for mkl in listdir(mkldir) if mkl.startswith('mkl_')]
