import logging
import os
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


def delete_file(path):
    if os.path.isfile(path):
        os.remove(path)


def parse_string_to_dicts(input_string, split_caracter=",", ret_type="list"):
    """
    This function transform: 
    
    "record_type:article\nauthor:John Doe\ntitle:Python Programming"
        TO
    [{'record_type': 'article'}, {'author': 'John Doe'}, {'title': 'Python Programming'}]
    """    
    # Dividir a string em linhas
    lines = input_string.split(split_caracter)
            
    # Lista para armazenar os dicionários
    if ret_type == "list":
        ret_items = [] 
    else:
        ret_items = {}
    
    # Iterar sobre cada linha
    for line in lines:
        # Dividir a linha em chave e valor usando ":" como separador
        parts = line.split(":")
        # Verificar se a linha está no formato correto
        if len(parts) == 2:
            # Criar um dicionário com a chave e o valor e adicionar à lista
            if ret_type == "list":
                ret_items.append({parts[0]: parts[1]})
            else: 
                ret_items.update({parts[0]: parts[1]})

    return ret_items


def replace_spaces_broken_lines(dictionary):
    """
    Replaces spaces in dictionary keys with newlines.

    Args:
    dictionary: The dictionary with keys that may contain spaces.

    Returns:
    A new dictionary with the modified keys.
    """

    new_dict = {}
    for key, value in dictionary.items():
        new_key = key.replace(" ", "\n")
        new_dict[new_key] = value
    return new_dict
