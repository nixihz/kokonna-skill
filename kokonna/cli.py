"""Command-line interface for the KoKonna OpenAPI client.

Top-level commands::

    kokonna config set-key <KEY>
    kokonna config show
    kokonna device info
    kokonna image list
    kokonna image upload <FILE> [--name NAME]
    kokonna image delete <ID>
    kokonna image download <ID> [--output PATH]
    kokonna image display <ID>
    kokonna image display-by-name <NAME>

All commands that talk to the API read the API key from
``$KOKONNA_API_KEY`` or ``~/.kokonna/config.json``.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click

from . import __version__
from .client import KokonnaClient
from .config import (
    API_KEY_ENV_VAR,
    Config,
    CONFIG_ENV_VAR,
    default_config_path,
    load_config,
    save_api_key,
)
from .exceptions import KokonnaError


# ---------------------------------------------------------------------- #
# Helpers                                                                #
# ---------------------------------------------------------------------- #

def _client() -> KokonnaClient:
    return KokonnaClient(load_config())


def _emit(data: Any, *, human: bool, as_json: bool) -> None:
    """Print ``data`` as JSON (default) or pretty (--human)."""
    if as_json:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return
    if human and isinstance(data, (dict, list)):
        click.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))
        return
    click.echo(str(data))


def _format_device(d: dict[str, Any]) -> str:
    """Compact, human-friendly device summary."""
    keys = [
        "nickname",
        "firmware",
        "online",
        "synced",
        "batteryLevel",
        "isCharging",
        "lastHeartbeat",
        "imageId",
        "coverId",
        "screenWidth",
        "screenHeight",
        "screenRotate",
        "switchType",
        "switchMinute",
        "timezone",
        "sdUsedSize",
        "point",
    ]
    lines = ["Device:"]
    for k in keys:
        if k in d:
            lines.append(f"  {k}: {d[k]}")
    return "\n".join(lines)


def _format_image_row(img: dict[str, Any]) -> str:
    current = " *" if img.get("current") else "  "
    return (
        f"{current} {img.get('id', '?'):<6} "
        f"{str(img.get('name', '')):<30} "
        f"{img.get('width', '?')}x{img.get('height', '?')} "
        f"{img.get('size', '?'):>8}B  "
        f"{img.get('createdAt', '')}"
    )


def _err(msg: str) -> None:
    click.echo(f"error: {msg}", err=True)


# ---------------------------------------------------------------------- #
# Root group                                                             #
# ---------------------------------------------------------------------- #

@click.group(
    name="kokonna",
    help="Control a KoKonna e-ink photo frame via the OpenAPI "
    "(https://kokonna.art/zh-hans/pages/openapi_cn).",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(__version__, prog_name="kokonna")
def cli() -> None:
    """KoKonna Frame CLI."""


# ---------------------------------------------------------------------- #
# config                                                                 #
# ---------------------------------------------------------------------- #

@cli.group(help="Manage CLI configuration (API key, config path).")
def config() -> None:
    pass


@config.command("set-key", help="Persist an API key to the config file.")
@click.argument("api_key")
def config_set_key(api_key: str) -> None:
    path = save_api_key(api_key.strip())
    click.echo(f"API key saved to {path}")


@config.command("show", help="Show the resolved config (key masked).")
def config_show() -> None:
    cfg = load_config()
    path = default_config_path()
    key = cfg.api_key
    masked = f"{key[:4]}…{key[-4:]}" if len(key) > 8 else ("(empty)" if not key else key)
    click.echo(
        json.dumps(
            {
                "config_path": str(path),
                "config_path_exists": path.is_file(),
                f"{API_KEY_ENV_VAR}_set": bool(__import__("os").environ.get(API_KEY_ENV_VAR)),
                f"{CONFIG_ENV_VAR}_override": __import__("os").environ.get(CONFIG_ENV_VAR),
                "api_key_masked": masked,
                "base_url": cfg.base_url,
                "timeout": cfg.timeout,
            },
            indent=2,
        )
    )


@config.command("path", help="Print the on-disk config file path.")
def config_path() -> None:
    click.echo(str(default_config_path()))


# ---------------------------------------------------------------------- #
# device                                                                 #
# ---------------------------------------------------------------------- #

@cli.group(help="Device-level operations.")
def device() -> None:
    pass


@device.command("info", help="Query live device state (firmware, battery, ...).")
@click.option("--human", is_flag=True, help="Pretty-print key=value summary.")
@click.option("--json", "as_json", is_flag=True, help="Force JSON output.")
def device_info(human: bool, as_json: bool) -> None:
    try:
        data = _client().get_device()
    except KokonnaError as exc:
        _err(str(exc))
        sys.exit(2)

    if human and not as_json:
        click.echo(_format_device(data))
    else:
        _emit(data, human=human, as_json=as_json)


# ---------------------------------------------------------------------- #
# image                                                                  #
# ---------------------------------------------------------------------- #

@cli.group(help="Image gallery operations.")
def image() -> None:
    pass


@image.command("list", help="List images on the device.")
@click.option("--human", is_flag=True, help="Pretty-print as a table.")
@click.option("--json", "as_json", is_flag=True, help="Force JSON output.")
def image_list(human: bool, as_json: bool) -> None:
    try:
        data = _client().list_images()
    except KokonnaError as exc:
        _err(str(exc))
        sys.exit(2)

    if human and not as_json:
        items = data.get("list", []) if isinstance(data, dict) else []
        click.echo(f"Total: {data.get('total', len(items)) if isinstance(data, dict) else len(items)}")
        if items:
            click.echo("  ID     NAME                           GEOM        SIZE      CREATED")
            for img in items:
                click.echo(_format_image_row(img))
        return
    _emit(data, human=human, as_json=as_json)


@image.command("upload", help="Upload an image file (auto-displayed).")
@click.argument("file", type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("--name", default=None, help="Override the image name (default: filename).")
@click.option("--json", "as_json", is_flag=True, help="Force JSON output.")
def image_upload(file: str, name: str | None, as_json: bool) -> None:
    try:
        data = _client().upload_image(file, name=name)
    except KokonnaError as exc:
        _err(str(exc))
        sys.exit(2)
    _emit(data, human=False, as_json=as_json)
    if not as_json and isinstance(data, dict) and "id" in data:
        click.echo(f"uploaded: id={data['id']} counter={data.get('counter')}")


@image.command("delete", help="Delete an image by id.")
@click.argument("image_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Force JSON output.")
def image_delete(image_id: int, as_json: bool) -> None:
    try:
        data = _client().delete_image(image_id)
    except KokonnaError as exc:
        _err(str(exc))
        sys.exit(2)
    _emit(data, human=False, as_json=as_json)


@image.command("download", help="Download an image to a local file.")
@click.argument("image_id", type=int)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Output path (default: <id>.<ext> in cwd).",
)
def image_download(image_id: int, output: str | None) -> None:
    try:
        client = _client()
        if output is None:
            ext = client.guess_extension(image_id)
            output = f"{image_id}.{ext}"
        data = client.download_image(image_id, output=output)
    except KokonnaError as exc:
        _err(str(exc))
        sys.exit(2)
    click.echo(f"wrote {len(data)} bytes to {output}")


@image.command("display", help="Display an image on the device by id.")
@click.argument("image_id", type=int)
@click.option("--json", "as_json", is_flag=True, help="Force JSON output.")
def image_display(image_id: int, as_json: bool) -> None:
    try:
        data = _client().display_image_by_id(image_id)
    except KokonnaError as exc:
        _err(str(exc))
        sys.exit(2)
    _emit(data, human=False, as_json=as_json)


@image.command("display-by-name", help="Display an image on the device by name.")
@click.argument("image_name")
@click.option("--json", "as_json", is_flag=True, help="Force JSON output.")
def image_display_by_name(image_name: str, as_json: bool) -> None:
    try:
        data = _client().display_image_by_name(image_name)
    except KokonnaError as exc:
        _err(str(exc))
        sys.exit(2)
    _emit(data, human=False, as_json=as_json)


# ---------------------------------------------------------------------- #
# entry point                                                            #
# ---------------------------------------------------------------------- #

def main() -> None:
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
