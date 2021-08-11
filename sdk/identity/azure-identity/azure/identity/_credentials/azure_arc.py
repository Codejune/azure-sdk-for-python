# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
import functools
import os
from typing import TYPE_CHECKING

from azure.core.exceptions import ClientAuthenticationError
from azure.core.pipeline.transport import HttpRequest
from azure.core.pipeline.policies import HTTPPolicy

from .. import CredentialUnavailableError
from .._constants import EnvironmentVariables
from .._internal.managed_identity_client import ManagedIdentityClient
from .._internal.get_token_mixin import GetTokenMixin

if TYPE_CHECKING:
    # pylint:disable=unused-import,ungrouped-imports
    from typing import Any, Optional, Union
    from azure.core.credentials import AccessToken
    from azure.core.pipeline import PipelineRequest, PipelineResponse
    from azure.core.pipeline.policies import SansIOHTTPPolicy

    PolicyType = Union[HTTPPolicy, SansIOHTTPPolicy]


class AzureArcCredential(GetTokenMixin):
    def __init__(self, **kwargs):
        # type: (**Any) -> None
        super(AzureArcCredential, self).__init__()

        url = os.environ.get(EnvironmentVariables.IDENTITY_ENDPOINT)
        imds = os.environ.get(EnvironmentVariables.IMDS_ENDPOINT)
        self._available = url and imds
        if self._available:
            self._client = ManagedIdentityClient(
                _per_retry_policies=[ArcChallengeAuthPolicy()],
                request_factory=functools.partial(_get_request, url),
                **kwargs
            )

    def get_token(self, *scopes, **kwargs):
        # type: (*str, **Any) -> AccessToken
        if not self._available:
            raise CredentialUnavailableError(
                message="Azure Arc managed identity configuration not found in environment"
            )
        return super(AzureArcCredential, self).get_token(*scopes, **kwargs)

    def _acquire_token_silently(self, *scopes, **kwargs):
        # type: (*str, **Any) -> Optional[AccessToken]
        return self._client.get_cached_token(*scopes)

    def _request_token(self, *scopes, **kwargs):
        # type: (*str, **Any) -> AccessToken
        return self._client.request_token(*scopes, **kwargs)


def _get_request(url, scope, identity_config):
    # type: (str, str, dict) -> HttpRequest
    if identity_config:
        raise ClientAuthenticationError(
            message="User assigned managed identities are not supported by Azure Arc. To authenticate with the system "
            "assigned identity omit the client id when constructing the credential, and if authenticating with "
            "DefaultAzureCredential ensure the AZURE_CLIENT_ID environment variable is not set."
        )

    request = HttpRequest("GET", url)
    request.format_parameters(dict({"api-version": "2019-11-01", "resource": scope}, **identity_config))
    return request


def _get_secret_key(response):
    # type: (PipelineResponse) -> str
    # expecting header containing path to secret key file
    header = response.http_response.headers.get("WWW-Authenticate")
    if not header:
        raise ClientAuthenticationError(message="Did not receive a value from WWW-Authenticate header")

    # expecting header with structure like 'Basic realm=<file path>'
    try:
        key_file = header.split("=")[1]
    except IndexError:
        raise ClientAuthenticationError(
            message="Did not receive a correct value from WWW-Authenticate header: {}".format(header)
        )
    with open(key_file, "r") as file:
        try:
            return file.read()
        except Exception as error:  # pylint:disable=broad-except
            # user is expected to have obtained read permission prior to this being called
            raise ClientAuthenticationError(message="Could not read file {} contents: {}".format(key_file, error))


class ArcChallengeAuthPolicy(HTTPPolicy):
    """Policy for handling Azure Arc's challenge authentication"""

    def send(self, request):
        # type: (PipelineRequest) -> PipelineResponse
        request.http_request.headers["Metadata"] = "true"
        response = self.next.send(request)

        if response.http_response.status_code == 401:
            secret_key = _get_secret_key(response)
            request.http_request.headers["Authorization"] = "Basic {}".format(secret_key)
            response = self.next.send(request)

        return response
