from ..logger import logger
logger.debug("Started 'reading utils/system_info.py'")

import uuid
import platform

def get_location():
    '''
    Get Location information from ip-address for plugin download statistics.
    Returns a string like: "Santa Barbara, CA, United States"
    '''
    import requests
    try:
        response = requests.get("http://ipinfo.io/json")
        data = response.json()
        return data.get('city', 'Unknown') + ', ' + data.get('region', 'Unknown') + ', ' + data.get('country', 'Unknown')
    except Exception as e:
        logger.error(f"Error getting location: {e}")
        return "Unknown, Unknown, Unknown"

def get_system_info():
    """
    Returns basic system information useful for debugging
    """
    return {
        'os': platform.system(),
        'os_release': platform.release(),
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'architecture': platform.architecture()[0]
    }

logger.debug("Completed 'reading utils/system_info.py'") 