import logging
import re

import requests
from langcodes import standardize_tag, tag_is_valid
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Recoverable error without having to modify the data state on the client
    side, e.g. timeouts, errors from network partitioning, etc.
    """


class NonRetryableError(Exception):
    """Recoverable error without having to modify the data state on the client
    side, e.g. timeouts, errors from network partitioning, etc.
    """


def nestget(data, *path, default=None):
    """
    Get nested values from a dict or list.
    Args:
        data: dict or list
        path: path from dict or index in list
        default: "" if not found
    Returns:
        Return the data.
    Except:
        No exceptions.
        data = {'search': {'entry': [
                            {'dn': 'uid=014591631,c=br,ou=bluepages,o=ibm.com', 'attribute': [
                                    {'name': 'pdif', 'value': ['1'
                                        ]
                                    },
                                    {'name': 'passwordModifyTimestamp', 'value': ['20220829'
                                        ]
                                    },
                                    {'name': 'preferredFirstName', 'value': ['Jamil'
                                        ]
                                    },
                                    {'name': 'hrFirstName', 'value': ['Jamil'
                                        ]
                                    },
                                    {'name': 'notesMailDomain', 'value': ['IBMMail'
                                        ]
                                    },
                                    {'name': 'c', 'value': ['br'
                                        ]
                                    },
                                    {'name': 'manager', 'value': ['uid=011235631,c=br,ou=bluepages,o=ibm.com'
                                        ]
                                    }
                                ]
                            }
                        ], 'return': {'code': 0, 'message': 'Success', 'count': 1
                        }
                    }
                }
        Example: nestget(data, "search", "entry", 0, "attribute")
    """
    for key_or_index in path:
        try:
            data = data[key_or_index]
        except (KeyError, IndexError):
            return default
    return data


@retry(
    retry=retry_if_exception_type(RetryableError),
    wait=wait_exponential(multiplier=1, min=1, max=15),
    stop=stop_after_attempt(5),
)
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
        response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        logger.error("Erro fetching the content: %s, retry..., erro: %s" % (url, exc))
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
                "Erro fetching the content: %s, retry..., erro: %s" % (url, exc)
            )
            raise RetryableError(exc) from exc
        else:
            raise

    return response.content if not json else response.json()


def is_float(element: any) -> bool:
    # If you expect None to be passed:
    if element is None:
        return False
    try:
        float(element)
        return True
    except ValueError:
        return False


def is_int(element: any) -> bool:
    # If you expect None to be passed:
    if element is None:
        return False
    try:
        int(element)
        return True
    except ValueError:
        return False


def is_str(element: any) -> bool:
    # If you expect None to be passed:
    if element is None:
        return False
    try:
        str(element)
        return True
    except ValueError:
        return False


def language_iso(code):
    """
    This function standardize a language tag and check if is valid language.
    """
    code = re.split(r"-|_", code)[0] if code else ""
    if tag_is_valid(code):
        return standardize_tag(code)
    return ""
