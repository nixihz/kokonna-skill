# kokonna-skill

CLI + Hermes skill for the [KoKonna](https://kokonna.art) e-ink photo frame OpenAPI. Lets you (or an AI agent) push images to a Frame, manage its gallery, query device status, and download stored images — all from the terminal.

- **CLI source:** `kokonna/`
- **Hermes skill:** `skill/SKILL.md` (install with `ln -s "$(pwd)/skill" ~/.hermes/skills/kokonna`)
- **API reference:** <https://kokonna.art/zh-hans/pages/openapi_cn>
- **Chinese guide:** [docs/usage.zh-CN.md](docs/usage.zh-CN.md)

## Install

```bash
# recommended: pipx (isolated env, easy to upgrade)
pipx install .

# or: user-site install
pip install --user .

# verify
kokonna --version
kokonna --help
```

## Configure

The device API key is shown on the Frame's settings page. Save it once:

```bash
kokonna config set-key <API_KEY>
```

Or, for one-off scripts, set the env var:

```bash
export KOKONNA_API_KEY=***
```

The config file lives at `~/.kokonna/config.json` (override with `$KOKONNA_CONFIG`).

## Usage

```bash
# device state
kokonna device info
kokonna device info --human
kokonna device info --json | jq '.batteryLevel, .online'

# gallery
kokonna image list
kokonna image list --human
kokonna image upload ./photo.jpg
kokonna image upload ./photo.jpg --name sunset.jpg
kokonna image delete 123

# display
kokonna image display 123
kokonna image display-by-name sunset.jpg

# download
kokonna image download 123                # writes 123.jpg in cwd
kokonna image download 123 -o shot.jpg    # custom path
```

End-to-end "generate → push to frame" loop:

```bash
image-gen --prompt "..." --output ./out.png
kokonna image upload ./out.png
```

All commands exit non-zero on errors and print a short message to stderr (rate limit, auth failure, not found, etc.).

## Install the Hermes skill

```bash
ln -s "$(pwd)/skill" ~/.hermes/skills/kokonna
```

Then the skill is auto-discovered by Hermes. To uninstall:

```bash
rm ~/.hermes/skills/kokonna
```

## Develop

```bash
# install with test extras
pipx install -e .[test]   # or: pip install -e .[test]

# run unit tests (no network — HTTP is mocked)
pytest

# run from source without installing
python -m kokonna --help
```

## Project layout

```
kokonna-skill/
├── kokonna/                 # CLI package
│   ├── __init__.py
│   ├── __main__.py          # `python -m kokonna`
│   ├── cli.py               # click subcommands
│   ├── client.py            # API client
│   ├── config.py            # API key resolution + storage
│   └── exceptions.py        # typed errors
├── skill/
│   └── SKILL.md             # the Hermes skill
├── tests/
│   ├── test_client.py
│   └── test_config.py
├── examples/                # add helper scripts here
├── pyproject.toml
└── README.md
```

## API endpoint coverage

| Endpoint                         | CLI                                       | Method            |
| -------------------------------- | ----------------------------------------- | ----------------- |
| `POST /device`                   | `kokonna device info`                     | `get_device`      |
| `POST /upload`                   | `kokonna image upload <file>`             | `upload_image`    |
| `POST /listImages`               | `kokonna image list`                      | `list_images`     |
| `POST /deleteImage`              | `kokonna image delete <id>`               | `delete_image`    |
| `POST /displayImageById`         | `kokonna image display <id>`              | `display_image_by_id` |
| `POST /displayImageByName`       | `kokonna image display-by-name <name>`    | `display_image_by_name` |
| `GET /image/:apikey/:imageId`    | `kokonna image download <id> [-o PATH]`   | `download_image`  |

## License

MIT.
