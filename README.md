# kokonna-skill

CLI + Hermes skill for the [KoKonna](https://kokonna.art) e-ink photo frame OpenAPI. Lets you (or an AI agent) push images to a Frame, manage its gallery, query device status, and download stored images — all from the terminal.

- **CLI source:** `kokonna/`
- **Agent skill:** `skill/SKILL.md` (install with `npx skills add nixihz/kokonna-skill --skill kokonna --copy -y`)
- **API reference:** <https://kokonna.art/zh-hans/pages/openapi_cn>
- **中文文档:** [docs/usage.zh-CN.md](docs/usage.zh-CN.md)

## What gets installed

This project has two separate pieces:

| Piece | Purpose | Install command |
| --- | --- | --- |
| Agent skill | Teaches Codex/Hermes-compatible agents when and how to use KoKonna | `npx skills add nixihz/kokonna-skill --skill kokonna --copy -y` |
| Python CLI | Actually talks to the KoKonna OpenAPI and pushes images to the frame | `pipx install git+https://github.com/nixihz/kokonna-skill.git` |

Installing the skill alone is enough for agent discovery, but it does **not**
install the `kokonna` executable. To push images to the frame, install the CLI
and configure the device API key too.

## Quick start

```bash
# 1. Install the agent skill into the current project
npx skills add nixihz/kokonna-skill --skill kokonna --copy -y

# 2. Install the Python CLI
pipx install git+https://github.com/nixihz/kokonna-skill.git

# 3. Save the frame API key
kokonna config set-key <API_KEY>

# 4. Verify everything works
npx skills list --json
kokonna --version
kokonna device info --human
```

## Copy-paste agent prompt

Copy this into Codex, Hermes, or another terminal-capable coding agent:

```text
Please install and verify KoKonna support on this machine.

Do these steps:
1. Install the KoKonna agent skill for the current project:
   npx skills add nixihz/kokonna-skill --skill kokonna --copy -y
2. Verify it is visible:
   npx skills list --json
3. Install the KoKonna Python CLI:
   pipx install git+https://github.com/nixihz/kokonna-skill.git
   If pipx is missing, use python -m pip install --user git+https://github.com/nixihz/kokonna-skill.git and make sure the kokonna command is on PATH.
4. Verify the CLI:
   kokonna --version
   kokonna --help
5. Check whether an API key is already configured:
   kokonna config show
6. If api_key_masked is empty, ask me for my KoKonna Frame API key, then save it with:
   kokonna config set-key <API_KEY>
   Do not print the full API key in your final response.
7. Verify the device:
   kokonna device info --human

After installation, summarize what was installed, whether the skill is visible, whether the CLI works, and whether the device check passed.
```

## Install the CLI

From GitHub:

```bash
pipx install git+https://github.com/nixihz/kokonna-skill.git
```

From a local checkout:

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

## Install the skill

```bash
npx skills add nixihz/kokonna-skill --skill kokonna --copy -y
```

This installs the `kokonna` skill into the current project's agent skills
directory. For a user-level install, add `-g`:

```bash
npx skills add nixihz/kokonna-skill --skill kokonna --copy -g -y
```

Then verify the install:

```bash
npx skills list --json
```

For local development, you can also install directly from the checkout:

```bash
npx skills add . --skill kokonna --copy -y
```

After installing or updating skills in a running gateway/session, reload that
session if it does not pick up the new skill automatically.

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
