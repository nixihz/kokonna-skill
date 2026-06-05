---
name: kokonna
description: Control a KoKonna e-ink photo frame via the OpenAPI. Use when the user wants to upload an image to their Frame, list/manage the Frame's gallery, display an image on the Frame, query device status (battery, screen, firmware, heartbeat), or download a stored image. Triggers on mentions of "KoKonna", "Frame", "e-ink frame", "推送到相框", "上传到相框", or any task that needs to push visual content to a connected KoKonna device.
---

# KoKonna Frame Skill

Use this skill when the user wants to interact with a [KoKonna e-ink photo frame](https://kokonna.art) — uploading images, managing the gallery, switching what's displayed, or checking device status.

This skill is only the agent workflow. The actual frame operations are performed by the `kokonna` Python CLI. All commands require a device API key (Bearer token). **Always check whether the CLI is installed and configured before doing anything else.**

## Setup

**Step 1 — verify the CLI is available:**

```bash
which kokonna && kokonna --version
```

If missing, install it:

```bash
pipx install git+https://github.com/nixihz/kokonna-skill.git
# or from a local checkout:
# pipx install .
```

**Step 2 — verify the API key is configured:**

```bash
kokonna config show
```

If `api_key_masked` is `(empty)`, prompt the user to provide their device API key (visible on the Frame's settings page) and save it:

```bash
kokonna config set-key <API_KEY>
# or one-off:
KOKONNA_API_KEY=*** kokonna device info
```

**Step 3 — sanity-check the device is reachable:**

```bash
kokonna device info --human
```

If this returns an auth error, the key is wrong. If it returns "Too many requests", wait a minute and retry (limit: 20 req/min per device).

**Step 4 — confirm the physical mount orientation before generating/uploading images.** This is the #1 source of bad-looking frames.

`screenWidth` / `screenHeight` / `screenRotate` describe the **LCD panel**, not what the user sees. The visible area is the panel rotated by `screenRotate`. Known setup: `800×480` panel with `screenRotate: 270`, mounted vertically → effective display `480×800` (3:5 portrait). The device auto-crops uploaded images to this visible area, and the result is brutal — a 16:9 landscape photo on a portrait frame becomes a center slice.

**Always ask the user how the frame is physically mounted (horizontal / vertical) before generating an image for it.** Do not infer from `screenRotate` alone — confirm the mount.

`mmx` aspect-ratio cheat sheet (mmx does NOT support the frame's native 5:3):

| Frame mounted     | Effective display | Generate at | Why                              |
| ----------------- | ----------------- | ----------- | -------------------------------- |
| Vertical/portrait | 480×800 (3:5)     | `9:16`      | Closest to 3:5 (off by ~6%)      |
| Vertical/portrait | 480×800 (3:5)     | `2:3`       | Backup if 9:16 unavailable       |
| Horizontal        | 800×480 (5:3)     | `16:9`      | Closest to 5:3 (off by ~6%)      |
| Horizontal        | 800×480 (5:3)     | `3:2`       | Backup                           |

The device auto-crops, so off-ratio uploads are tolerable — but matching the **orientation** (portrait vs landscape) is non-negotiable.

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

1. Confirm the frame's physical mount (vertical / horizontal) with the user.
2. Generate / obtain an image file locally (PNG or JPEG) at the matching aspect ratio: `9:16` for portrait frames, `16:9` for landscape.
3. `kokonna image upload <file>` — the device auto-switches to the new image; response includes `id` and the new `counter`.
4. Optionally `kokonna image list --human` to confirm and capture the new id.
5. For a daily rotation, upload in the morning and use `display-by-name` later in the day if needed.

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
# 1. generate (use 9:16 for portrait, 16:9 for landscape)
mmx image generate --prompt "..." --aspect-ratio 9:16 --out-dir /tmp --out-prefix frame

# 2. upload + display in one step
kokonna image upload /tmp/frame_001.jpg
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

## Pitfalls

- **Generated image looks cropped/weird on the frame?** Wrong orientation. The most common cause is generating 16:9 landscape for a vertically-mounted frame — the device auto-crops to a thin center slice. Regenerate at 9:16 and re-upload.
- **`mmx` rejects `5:3` (or any non-listed ratio).** Valid set: `1:1 16:9 4:3 3:2 2:3 3:4 9:16 21:9`. Don't retry the same ratio — pick the closest valid one for the frame's mount orientation.
- **Upload returned 200 but frame still shows the old image.** E-ink refresh is slow; `synced` flips `false` → `true` after ~30–60s. Don't re-upload — wait and re-check with `kokonna device info`.
- **`can not find robot <key>` from `device info`** usually means the API key was reset on the Frame. Confirm with the user, then `kokonna config set-key <NEW_KEY>`.
- **Deleting the currently-displayed image** auto-switches to the next available one. The response's `imageId` is the new active id (or `null` if none remain). Don't be alarmed.
- **Download endpoint (`image download`) puts the API key in the URL path**, not the `Authorization` header. The CLI handles this correctly; do not try to construct the URL manually and pass the key in `Authorization`.
- **20 req/min per device.** If you're batch-uploading many images, pause ~3s between calls or the API starts returning 429.
- **`display-by-name` is case-sensitive and exact.** `photo.jpg` won't match `Photo.JPG` or `photo.jpg ` (with trailing space). List the gallery first to get the exact name.
- **Stale uploads in the gallery** (e.g. an earlier wrong-orientation image) stay on the device and consume space. Use `kokonna image delete <id>` to clean up after replacing them.

## Files

- CLI source: `kokonna/` (this directory)
- Reference API: <https://kokonna.art/zh-hans/pages/openapi_cn>
- Test the client (no network): `cd /opt/case/opensource/kokonna-skill && pytest`
