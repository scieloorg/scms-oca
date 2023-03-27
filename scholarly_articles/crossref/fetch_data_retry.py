import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

import logging


logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Recoverable error without having to modify the data state on the client
    side, e.g. timeouts, errors from network partitioning, etc.
    """

 
class NonRetryableError(Exception):
    """Recoverable error without having to modify the data state on the client
    side, e.g. timeouts, errors from network partitioning, etc.
    """


@retry(retry=retry_if_exception_type(RetryableError),
       wait=wait_exponential(multiplier=1, min=1, max=10),
       stop=stop_after_attempt(15))
def fetch_data(url, headers=None, json=False, timeout=2, verify=True):
    """
    Get the resource with HTTP
    Retry: Wait 2^x * 1 second between each retry starting with 4 seconds,
           then up to 10 seconds, then 10 seconds afterwards
    Args:
        url: URL address
        headers: HTTP headers
        json: True|False 
        verify: Verify the SSL. 
    Returns:
        Return a requests.response object.
    Except:
        Raise a RetryableError to retry.
    """

    try:
        logger.info("Fetching the URL: %s" % url)
        response = requests.get(url, headers=headers,
                                timeout=timeout, verify=verify)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.error(
            "Erro fetching the content: %s, retry..., erro: %s" %
            (url, exc))
        raise RetryableError(exc) from exc
    except (
        requests.exceptions.InvalidSchema,
        requests.exceptions.MissingSchema,
        requests.exceptions.InvalidURL,
    ) as exc:
        raise NonRetryableError(exc) from exc
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if 400 <= exc.response.status_code < 500:
            raise NonRetryableError(exc) from exc
        elif 500 <= exc.response.status_code < 600:
            logger.error(
                "Erro fetching the content: %s, retry..., erro: %s" %
                (url, exc))
            raise RetryableError(exc) from exc
        else:
            raise

    return response.content if not json else response.json()


def request_retry(url, total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]):
    s = requests.Session()
    
    retries = Retry(total=10,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504])

    s.mount('http://', HTTPAdapter(max_retries=retries))

    try:
        response = s.get(url)
        response.raise_for_status()
        logger.info(f'Request to {url} was successful.')
        
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f'Request to {url} failed: {e}')