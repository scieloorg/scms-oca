import requests

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

import logging


logger = logging.getLogger(__name__)


def request_retry(url, total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]):
    s = requests.Session()
    
    retries = Retry(total,
                    backoff_factor,
                    status_forcelist)

    s.mount('http://', HTTPAdapter(max_retries=retries))

    try:
        response = s.get(url)
        response.raise_for_status()
        logger.info(f'Request to {url} was successful.')
        
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f'Request to {url} failed: {e}')