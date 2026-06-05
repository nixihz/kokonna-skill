"""Unit tests for the KoKonna client. HTTP calls are mocked via ``responses``."""

from __future__ import annotations

import base64
import json

import pytest
import responses

from kokonna.client import KokonnaClient
from kokonna.config import Config
from kokonna.exceptions import (
    KokonnaAuthError,
    KokonnaNotFoundError,
    KokonnaRateLimitError,
    KokonnaServerError,
)

API_KEY = "test-key-123"
BASE = "https://api.galaxyguide.cn/openapi"


@pytest.fixture
def client() -> KokonnaClient:
    return KokonnaClient(Config(api_key=API_KEY))


# ----------------------------------------------------------------------- #
# Happy-path endpoint tests                                               #
# ----------------------------------------------------------------------- #

@responses.activate
def test_get_device(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/device",
        json={
            "firmware": "B100V050610",
            "nickname": "KoKonna",
            "lastHeartbeat": "2025-06-16T06:56:25.782Z",
            "isCharging": False,
            "batteryLevel": 100,
            "sdUsedSize": 0,
            "switchType": "queue",
            "switchMinute": 60,
            "imageId": 423,
            "coverId": None,
            "timezone": "Asia/Shanghai",
            "point": 30,
            "screenWidth": 800,
            "screenHeight": 480,
            "screenRotate": 270,
            "synced": True,
            "online": True,
        },
        status=200,
    )
    data = client.get_device()
    assert data["firmware"] == "B100V050610"
    assert data["batteryLevel"] == 100
    # Auth header was set.
    assert responses.calls[0].request.headers["Authorization"] == f"Bearer {API_KEY}"


@responses.activate
def test_upload_image_sends_raw_base64(client: KokonnaClient, tmp_path) -> None:
    img_path = tmp_path / "hello.png"
    img_path.write_bytes(b"\x89PNG_FAKE")
    responses.add(
        responses.POST,
        f"{BASE}/upload",
        json={"id": 789, "counter": 10},
        status=200,
    )

    data = client.upload_image(img_path)
    assert data == {"id": 789, "counter": 10}

    sent = json.loads(responses.calls[0].request.body)
    assert sent["name"] == "hello.png"
    assert sent["base64"] == base64.b64encode(b"\x89PNG_FAKE").decode("ascii")
    # The base64 payload must NOT have a data URL prefix.
    assert "," not in sent["base64"]


@responses.activate
def test_upload_image_with_name_override(client: KokonnaClient, tmp_path) -> None:
    img_path = tmp_path / "photo.jpg"
    img_path.write_bytes(b"jpeg-bytes")
    responses.add(
        responses.POST,
        f"{BASE}/upload",
        json={"id": 1, "counter": 1},
        status=200,
    )
    client.upload_image(img_path, name="renamed.jpg")
    sent = json.loads(responses.calls[0].request.body)
    assert sent["name"] == "renamed.jpg"


@responses.activate
def test_list_images(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/listImages",
        json={
            "total": 1,
            "list": [
                {
                    "id": 1,
                    "name": "a.jpg",
                    "fileId": "abc.jpg",
                    "size": 100,
                    "type": "image/jpeg",
                    "width": 800,
                    "height": 480,
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-01T00:00:00.000Z",
                    "current": True,
                }
            ],
        },
        status=200,
    )
    data = client.list_images()
    assert data["total"] == 1
    assert data["list"][0]["current"] is True


@responses.activate
def test_delete_image(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/deleteImage",
        json={"success": True, "id": 5, "imageId": 4, "counter": 11},
        status=200,
    )
    data = client.delete_image(5)
    assert data["id"] == 5
    sent = json.loads(responses.calls[0].request.body)
    assert sent == {"imageId": 5}


@responses.activate
def test_display_image_by_id(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/displayImageById",
        json={"success": True},
        status=200,
    )
    assert client.display_image_by_id(42) == {"success": True}
    sent = json.loads(responses.calls[0].request.body)
    assert sent == {"imageId": 42}


@responses.activate
def test_display_image_by_name(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/displayImageByName",
        json={"success": True},
        status=200,
    )
    assert client.display_image_by_name("photo.jpg") == {"success": True}
    sent = json.loads(responses.calls[0].request.body)
    assert sent == {"imageName": "photo.jpg"}


@responses.activate
def test_download_image_writes_to_disk(client: KokonnaClient, tmp_path) -> None:
    out = tmp_path / "out.jpg"
    responses.add(
        responses.GET,
        f"{BASE}/image/{API_KEY}/7",
        body=b"\xff\xd8\xff_FAKE_JPEG",
        status=200,
        content_type="image/jpeg",
    )
    data = client.download_image(7, output=out)
    assert data == b"\xff\xd8\xff_FAKE_JPEG"
    assert out.read_bytes() == b"\xff\xd8\xff_FAKE_JPEG"
    # The Authorization header is intentionally NOT set for this endpoint.
    assert "Authorization" not in responses.calls[0].request.headers


@responses.activate
def test_guess_extension(client: KokonnaClient) -> None:
    responses.add(
        responses.GET,
        f"{BASE}/image/{API_KEY}/9",
        body=b"x",
        status=200,
        content_type="image/png",
    )
    assert client.guess_extension(9) == "png"


# ----------------------------------------------------------------------- #
# Error mapping                                                          #
# ----------------------------------------------------------------------- #

def test_no_api_key_raises() -> None:
    bare = KokonnaClient(Config(api_key=""))
    with pytest.raises(KokonnaAuthError):
        bare.get_device()


def test_no_api_key_raises_on_upload(tmp_path) -> None:
    p = tmp_path / "a.jpg"
    p.write_bytes(b"x")
    bare = KokonnaClient(Config(api_key=""))
    with pytest.raises(KokonnaAuthError):
        bare.upload_image(p)


@responses.activate
def test_rate_limit_429(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/device",
        json={"message": "Too many requests, please try again later."},
        status=429,
    )
    with pytest.raises(KokonnaRateLimitError):
        client.get_device()


@responses.activate
def test_unknown_method_404(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/device",
        json={"message": "can not find method /wat"},
        status=404,
    )
    with pytest.raises(KokonnaNotFoundError):
        client.get_device()


@responses.activate
def test_unknown_robot_500_is_auth_error(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/device",
        json={"message": f"can not find robot {API_KEY}"},
        status=500,
    )
    with pytest.raises(KokonnaAuthError):
        client.get_device()


@responses.activate
def test_image_not_found_500_is_not_found(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/deleteImage",
        json={"message": "image not found"},
        status=500,
    )
    with pytest.raises(KokonnaNotFoundError):
        client.delete_image(1)


@responses.activate
def test_other_500_is_server_error(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/device",
        json={"message": "database exploded"},
        status=500,
    )
    with pytest.raises(KokonnaServerError):
        client.get_device()


@responses.activate
def test_empty_image_id_500(client: KokonnaClient) -> None:
    responses.add(
        responses.POST,
        f"{BASE}/deleteImage",
        json={"message": "imageId is empty"},
        status=500,
    )
    with pytest.raises(KokonnaServerError):
        client.delete_image(1)


# ----------------------------------------------------------------------- #
# Argument validation                                                    #
# ----------------------------------------------------------------------- #

def test_invalid_image_id_rejected_locally(client: KokonnaClient) -> None:
    with pytest.raises(Exception):
        client.delete_image(0)
    with pytest.raises(Exception):
        client.display_image_by_id(-3)


def test_empty_name_rejected_locally(client: KokonnaClient) -> None:
    with pytest.raises(Exception):
        client.display_image_by_name("")
