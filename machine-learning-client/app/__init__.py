"""Machine learning client application initialization."""

# pylint: disable=wrong-import-position,pointless-string-statement

from __future__ import annotations
import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests  # pylint: disable=import-error

"""
machine-learning-client.app package initializer.

Provides a small, lightweight MachineLearningClient, configuration dataclass,
and a factory to create a client with sensible defaults.
"""


__version__ = "0.1.0"


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


@dataclass(frozen=True)
class Config:  # pylint: disable=too-few-public-methods
    """Configuration for MachineLearningClient."""

    host: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout: float = 10.0
    verify_ssl: bool = True
    user_agent: str = f"machine-learning-client/{__version__}"


# default config constructed from environment variables when available
DEFAULT_CONFIG = Config(
    host=os.getenv("ML_CLIENT_HOST", "http://localhost:8000"),
    api_key=os.getenv("ML_CLIENT_API_KEY"),
    timeout=float(os.getenv("ML_CLIENT_TIMEOUT", "10.0")),
    verify_ssl=(
        os.getenv("ML_CLIENT_VERIFY_SSL", "true").lower() not in ("0", "false")
    ),
)


class MachineLearningClient: # pylint: disable=too-few-public-methods
    """
    Minimal client for interacting with a machine learning model server.

    Usage:
        cfg = Config(host="https://ml.example", api_key="secret")
        client = MachineLearningClient(cfg)
        result = client.predict({"text": "hello"})
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})
        if self.config.api_key:
            self.session.headers.update(
                {"Authorization": f"Bearer {self.config.api_key}"}
            )
        logger.debug(
            "Initialized MachineLearningClient with host=%s", self.config.host
        )

    def _url(self, path: str) -> str:
        return f"{self.config.host.rstrip('/')}/{path.lstrip('/')}"

    def predict(
        self, payload: Dict[str, Any], endpoint: str = "/predict"
    ) -> Dict[str, Any]:
        """
        Send a prediction request to the model server.

        Args:
            payload: JSON-serializable input for the model.
            endpoint: Relative endpoint on the server (default: /predict).

        Returns:
            Parsed JSON response from the server.

        Raises:
            requests.HTTPError on non-2xx responses.
            requests.RequestException on network errors.
            ValueError if response is not valid JSON.
        """
        url = self._url(endpoint)
        logger.debug("Sending predict request to %s with payload=%s", url, payload)
        resp = self.session.post(
            url,
            json=payload,
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError:
            logger.error("Predict request failed: %s %s", resp.status_code, resp.text)
            raise
        try:
            return resp.json()
        except ValueError as exc:  # pylint: disable=unused-variable
            logger.error("Invalid JSON response from %s: %s", url, resp.text)
            raise


def create_client(config: Optional[Config] = None) -> MachineLearningClient:
    """Factory to create a MachineLearningClient with the given config or defaults."""
    return MachineLearningClient(config)


# package exports
__all__ = [
    "Config",
    "DEFAULT_CONFIG",
    "MachineLearningClient",
    "create_client",
    "__version__",
]
