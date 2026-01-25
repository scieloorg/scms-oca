import ssl
from collections.abc import Iterable

import httpx
from httpx._types import AuthTypes
from oaipmh_scythe import Scythe
from oaipmh_scythe.__about__ import __version__
from oaipmh_scythe.iterator import BaseOAIIterator, OAIItemIterator
from oaipmh_scythe.models import OAIItem
from oaipmh_scythe.utils import log_response
from sickle import Sickle

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)

OAI_NAMESPACE: str = "{http://www.openarchives.org/OAI/2.0/}"


class CustomScythe(Scythe):
    def __init__(
        self,
        endpoint: str,
        verify: ssl.SSLContext | str | bool = True,
        http_method: str = "GET",
        iterator: type[BaseOAIIterator] = OAIItemIterator,
        max_retries: int = 0,
        retry_status_codes: Iterable[int] | None = None,
        default_retry_after: int | float = 60,
        class_mapping: dict[str, type[OAIItem]] | None = None,
        encoding: str = "utf-8",
        auth: AuthTypes | None = None,
        timeout: int | float = 60,
    ):
        super().__init__(
            endpoint,
            http_method,
            iterator,
            max_retries,
            retry_status_codes,
            default_retry_after,
            class_mapping,
            encoding,
            auth,
            timeout,
        )
        self.verify = verify

    @property
    def client(self) -> httpx.Client:
        """Provide a reusable HTTP client instance for making requests.

        This property ensures that an `httpx.Client` instance is created and maintained for
        the lifecycle of the `Scythe` instance. It handles the creation of the client and
        ensures that a new client is created if the existing one is closed.

        Returns:
            A reusable HTTP client instance for making HTTP requests.
        """
        if self._client is None or self._client.is_closed:
            headers = {"Accept": "text/xml; charset=utf-8", "user-agent": USER_AGENT}
            self._client = httpx.Client(
                headers=headers,
                timeout=self.timeout,
                auth=self.auth,
                default_encoding=self.encoding,
                verify=self.verify,  # overwrite
                event_hooks={"response": [log_response]},
            )
        return self._client


def service_oai_pmh_scythe(
    url,
    metadata_prefix="oai_dc",
    from_date=None,
    until_date=None,
    verify=True,
    ignore_deleted=True,
):
    scythe = CustomScythe(url, verify=verify)

    params = {"metadata_prefix": metadata_prefix}

    if from_date:
        params["from_"] = from_date

    if until_date:
        params["until"] = until_date
    if ignore_deleted:
        params["ignore_deleted"] = ignore_deleted

    recs = scythe.list_records(**params)
    return recs


def service_oai_pmh_sickle(
    url, metadata_prefix="oai_dc", from_date=None, until_date=None, verify=False
):
    URL = url
    sickle = Sickle(URL, verify=verify)
    params = {"metadataPrefix": metadata_prefix}

    if from_date:
        params["from_"] = from_date

    if until_date:
        params["until"] = until_date

    recs = sickle.ListRecords(**params)
    return recs
