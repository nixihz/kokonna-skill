"""Synchronous HTTP client for the KoKonna Frame OpenAPI.

Reference: https://kokonna.art/zh-hans/pages/openapi_cn

The client is intentionally tiny: one method per documented endpoint, a
single ``_request`` helper that handles auth headers, error mapping, and
JSON (de)serialization. The one exception is the binary-download endpoint
(``GET /image/:apikey/:imageId``), which returns raw bytes.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

import requests

from .config import Config
from .exceptions import (
    KokonnaAuthError,
    KokonnaError,
    KokonnaNotFoundError,
    KokonnaRateLimitError,
    KokonnaServerError,
)

DEFAULT_BASE_URL = "https://api.galaxyguide.cn/openapi"
DEFAULT_TIMEOUT = 60.0


class KokonnaClient:
    """Thin wrapper around the KoKonna OpenAPI."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config(api_key="")
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def get_device(self) -> dict[str, Any]:
        """Return the live state of the Frame (firmware, battery, screen, ...)."""
        return self._request("POST", "/device", json={})

    def upload_image(self, file: str | Path, name: str | None = None) -> dict[str, Any]:
        """Upload an image file to the device.

        ``file`` may be a path or a ``Path`` object. Returns ``{"id", "counter"}``
        on success.
        """
        path = Path(file).expanduser()
        if not path.is_file():
            raise KokonnaError(f"file not found: {path}")

        data = base64.b64encode(path.read_bytes()).decode("ascii")
        body: dict[str, Any] = {"base64": data}
        if name:
            body["name"] = name
        else:
            # Server defaults to the original filename if omitted, but we
            # send it explicitly so the name is preserved across clients.
            body["name"] = path.name

        return self._request("POST", "/upload", json=body)

    def list_images(self) -> dict[str, Any]:
        """Return ``{"total", "list": [...]}`` of images on the device."""
        return self._request("POST", "/listImages", json={})

    def delete_image(self, image_id: int) -> dict[str, Any]:
        """Delete an image and return the new active image / counter."""
        if not isinstance(image_id, int) or image_id <= 0:
            raise KokonnaError("imageId must be a positive integer")
        return self._request("POST", "/deleteImage", json={"imageId": image_id})

    def display_image_by_id(self, image_id: int) -> dict[str, Any]:
        """Switch the device display to the given image id."""
        if not isinstance(image_id, int) or image_id <= 0:
            raise KokonnaError("imageId must be a positive integer")
        return self._request("POST", "/displayImageById", json={"imageId": image_id})

    def display_image_by_name(self, image_name: str) -> dict[str, Any]:
        """Switch the device display to the given image name."""
        if not image_name:
            raise KokonnaError("imageName must be non-empty")
        return self._request(
            "POST", "/displayImageByName", json={"imageName": image_name}
        )

    def download_image(
        self, image_id: int, output: str | Path | None = None
    ) -> bytes:
        """Fetch a stored image as raw bytes. If ``output`` is given, write
        to that path and return the bytes too.

        The API key is sent in the URL path for this endpoint, so the
        ``Authorization`` header is intentionally NOT set.
        """
        if not isinstance(image_id, int) or image_id <= 0:
            raise KokonnaError("imageId must be a positive integer")
        if not self.config.has_api_key:
            raise KokonnaAuthError(
                "API key required to download images (set via `kokonna config set-key` "
                "or the KOKONNA_API_KEY env var)"
            )

        url = f"{self.config.base_url.rstrip('/')}/image/{self.config.api_key}/{image_id}"
        try:
            resp = self._session.get(url, timeout=self.config.timeout, allow_redirects=True)
        except requests.RequestException as exc:
            raise KokonnaServerError(f"network error: {exc}") from exc

        self._raise_for_status(resp, expect_json=False)
        data = resp.content

        if output is not None:
            out_path = Path(output).expanduser()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(data)
        return data

    def guess_extension(self, image_id: int) -> str:
        """Heuristic: download the image (cheap) and pick an extension from
        the response Content-Type. The bytes are discarded. Use
        :meth:`download_image` if you actually need the bytes."""
        if not self.config.has_api_key:
            raise KokonnaAuthError("API key required")
        url = f"{self.config.base_url.rstrip('/')}/image/{self.config.api_key}/{image_id}"
        try:
            resp = self._session.get(
                url, timeout=self.config.timeout, allow_redirects=True, stream=True
            )
        except requests.RequestException as exc:
            raise KokonnaServerError(f"network error: {exc}") from exc
        self._raise_for_status(resp, expect_json=False)
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        resp.close()
        if ctype:
            ext = mimetypes.guess_extension(ctype)
            if ext:
                return ext.lstrip(".") or "bin"
        return "jpg"

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if not self.config.has_api_key:
            raise KokonnaAuthError(
                "API key not configured. Run `kokonna config set-key <KEY>` "
                "or set the KOKONNA_API_KEY environment variable."
            )

        url = f"{self.config.base_url.rstrip('/')}{path}"
        headers = kwargs.pop("headers", {}) or {}
        headers.setdefault("Authorization", f"Bearer {self.config.api_key}")
        headers.setdefault("Content-Type", "application/json")

        try:
            resp = self._session.request(
                method,
                url,
                headers=headers,
                timeout=self.config.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise KokonnaServerError(f"network error: {exc}") from exc

        self._raise_for_status(resp, expect_json=True)
        try:
            return resp.json()
        except ValueError as exc:
            raise KokonnaServerError(
                f"server returned non-JSON body (HTTP {resp.status_code}): "
                f"{resp.text[:200]!r}"
            ) from exc

    @staticmethod
    def _raise_for_status(resp: requests.Response, *, expect_json: bool) -> None:
        if resp.ok:
            return

        # Best-effort JSON body for error messages. Some endpoints return
        # plain text on 404 (e.g. the binary download endpoint).
        message: str | None = None
        if expect_json:
            try:
                payload = resp.json()
                if isinstance(payload, dict):
                    raw = payload.get("message")
                    if isinstance(raw, str):
                        message = raw
            except ValueError:
                message = None
        if message is None:
            text = (resp.text or "").strip()
            message = text or f"HTTP {resp.status_code}"

        status = resp.status_code
        if status == 429 or "too many requests" in message.lower():
            raise KokonnaRateLimitError(message)
        if status == 404 or "can not find method" in message:
            raise KokonnaNotFoundError(message)
        if "can not find robot" in message:
            raise KokonnaAuthError(message)
        if "not found" in message.lower():
            # Image / method not founds are surfaced by the server as 500s.
            raise KokonnaNotFoundError(message)
        if 500 <= status < 600:
            raise KokonnaServerError(f"{status}: {message}")
        raise KokonnaError(f"{status}: {message}")
