---
name: kokonna
description: Control a KoKonna e-ink photo frame via the OpenAPI. Use when the user wants to upload an image to their Frame, list/manage the Frame's gallery, display an image on the Frame, query device status (battery, screen, firmware, heartbeat), or download a stored image. Triggers on mentions of "KoKonna", "Frame", "e-ink frame", "推送到相框", "上传到相框", or any task that needs to push visual content to a connected KoKonna device.
---

# KoKonna Frame Skill

Use this skill when the user wants to interact with a [KoKonna e-ink photo frame](https://kokonna.art) — uploading images, managing the gallery, switching what's displayed, or checking device status.

The skill wraps the `kokonna` Python CLI installed in the same project (`/opt/case/opensource/kokonna-skill`). All commands require a device API key (Bearer token). **Always check whether the CLI is installed and configured before doing anything else.**

## Setup

**Step 1 — verify the CLI is available:**

```bash
which kokonna && kokonna --version
```

If missing, install it:

```bash
cd /opt/case/opensource/kokonna-skill
pipx install .          # recommended (isolated env)
# or: pip install --user .
```

**Step 2 — verify the API key is configured:**

```bash
kokonna config show
```

If `api_key_masked` is `(empty)`, prompt the user to provide their device API key (visible on the Frame's settings page) and save it:

```bash
kokonna config set-key <API_KEY>
# or one-off:
KOKONNA_API_KEY=<API_KEY> kokonna device info
```

**Step 3 — sanity-check the device is reachable:**

```bash
kokonna device info --human
```

If this returns an auth error, the key is wrong. If it returns "Too many requests", wait a minute and retry (limit: 20 req/min per device).

## When to use which command

| User intent                                          | Command                                                    |
| ---------------------------------------------------- | ---------------------------------------------------------- |
| Check battery, firmware, screen, online status       | `kokonna device info [--human]`                            |
| Push a new image to the Frame (auto-displays)        | `kokonna image upload <path> [--name NAME]`                |
| List everything currently on the device              | `kokonna image list [--human]`                             |
| Switch what's on the Frame to a specific image       | `kokonna image display <id>` or `display-by-name <name>`   |
| Pull an image back from the Frame to the local disk  | `kokonna image download <id> [-o path.jpg]`                |
| Remove an old image from the device                  | `kokonna image delete <id>`                                |
| Update or rotate the stored API key                  | `kokonna config set-key <KEY>`                             |

For an end-to-end "generate → push to frame" workflow, the typical sequence is:

1. Generate / obtain an image file locally (PNG or JPEG, ideally matching the frame's `screenWidth` × `screenHeight` ratio from `device info`).
2. `kokonna image upload <file>` — the device auto-switches to the new image; response includes `id` and the new `counter`.
3. Optionally `kokonna image list --human` to confirm and capture the new id.
4. For a daily rotation, upload in the morning and use `display-by-name` later in the day if needed.

## Important rules

- **Rate limit: 20 requests per minute per device key.** Batch operations and avoid polling.
- **Max payload: 50 MB per request.** Don't try to upload multi-megapixel images; resize to the frame's screen dimensions first.
- **The `base64` field must be raw base64** — no `data:image/jpeg;base64,` prefix. The CLI handles this correctly.
- **Image-name lookups (`display-by-name`) require the exact name** as returned by `image list`. Filenames are case-sensitive.
- **Deleting the currently active image** causes the server to auto-switch to the next available image. The response's `imageId` field reflects the new active id (or `null` if none remain).
- **For binary downloads (`image download`), the API key travels in the URL path**, not the Authorization header. The CLI handles this — do not try to construct the URL manually and pass the key in `Authorization`.

## Common patterns

**Pipeline a freshly-generated image straight to the frame:**

```bash
# 1. generate (example: an image-gen CLI writing to ./out.png)
image-gen --prompt "..." --output ./out.png

# 2. upload + display in one step
kokonna image upload ./out.png
```

**Build a status dashboard:**

```bash
kokonna device info --json | jq '{nickname, batteryLevel, online, synced, lastHeartbeat, imageId}'
kokonna image list --json | jq '.list | map({id, name, current})'
```

**Pull everything currently on the frame as a local archive:**

```bash
mkdir -p ~/frame-archive
kokonna image list --json | jq -r '.list[].id' | while read id; do
  kokonna image download "$id" -o ~/frame-archive/"$id.jpg"
done
```

## Error handling

The CLI exits non-zero on errors and prints a short message to stderr. Most common cases:

- `error: API key not configured...` — run `kokonna config set-key <KEY>`.
- `error: can not find robot <key>` — wrong API key, or device was reset.
- `error: image not found` — bad image id, or it belongs to a different device.
- `error: Too many requests, please try again later.` — back off and retry after ~60s.

When the CLI exits with an error, surface the message to the user plainly — don't try to parse the JSON body manually.

## Files

- CLI source: `kokonna/` (this directory)
- Reference API: <https://kokonna.art/zh-hans/pages/openapi_cn>
- Test the client (no network): `cd /opt/case/opensource/kokonna-skill && pytest`
