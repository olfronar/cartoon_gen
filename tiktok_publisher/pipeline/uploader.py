from __future__ import annotations

import json
import logging
import math
import time
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

# Chunk constraints (bytes)
_MIN_CHUNK = 5 * 1024 * 1024  # 5 MB
_DEFAULT_CHUNK = 10 * 1024 * 1024  # 10 MB
_MAX_CHUNK = 64 * 1024 * 1024  # 64 MB


def upload_video(
    access_token: str,
    video_path: Path,
) -> str:
    """Upload a video to TikTok inbox as draft. Returns the publish_id."""
    video_size = video_path.stat().st_size
    chunk_size = _compute_chunk_size(video_size)

    logger.info("Uploading %s (%.1f MB)", video_path.name, video_size / 1024 / 1024)

    publish_id, upload_url = init_upload(access_token, video_size, chunk_size)

    upload_chunks(upload_url, video_path, chunk_size)

    status = poll_status(access_token, publish_id)
    logger.info("Upload status: %s", status.get("status"))

    return publish_id


def init_upload(
    access_token: str,
    video_size: int,
    chunk_size: int,
) -> tuple[str, str]:
    """Initialize a TikTok inbox/draft upload. Returns (publish_id, upload_url)."""
    total_chunks = math.ceil(video_size / chunk_size)

    body = json.dumps(
        {
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": total_chunks,
            },
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        _INBOX_INIT_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        method="POST",
    )

    result = _api_request(req)

    error = result.get("error", {})
    if error.get("code") not in ("ok", None):
        raise RuntimeError(f"Upload init failed: {error.get('message', error.get('code'))}")

    data = result["data"]
    return data["publish_id"], data["upload_url"]


def upload_chunks(upload_url: str, video_path: Path, chunk_size: int) -> None:
    """Upload video file in sequential chunks."""
    total_size = video_path.stat().st_size

    with open(video_path, "rb") as f:
        offset = 0
        chunk_num = 0
        while offset < total_size:
            chunk_data = f.read(chunk_size)
            chunk_len = len(chunk_data)
            end = offset + chunk_len - 1

            req = urllib.request.Request(
                upload_url,
                data=chunk_data,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Length": str(chunk_len),
                    "Content-Range": f"bytes {offset}-{end}/{total_size}",
                },
                method="PUT",
            )

            with urllib.request.urlopen(req, timeout=120) as resp:
                status = resp.status

            chunk_num += 1
            logger.info(
                "  Chunk %d: %d-%d/%d (HTTP %d)",
                chunk_num,
                offset,
                end,
                total_size,
                status,
            )

            offset += chunk_len


def poll_status(
    access_token: str,
    publish_id: str,
    max_attempts: int = 30,
    interval: int = 5,
) -> dict:
    """Poll upload status until completion or failure."""
    body = json.dumps({"publish_id": publish_id}).encode("utf-8")

    status = ""
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            _STATUS_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            method="POST",
        )

        result = _api_request(req)

        data = result.get("data", {})
        status = data.get("status", "")

        if status in ("PUBLISH_COMPLETE", "SEND_TO_USER_INBOX"):
            return data
        if status == "FAILED":
            raise RuntimeError(f"Upload failed: {data.get('fail_reason', 'unknown')}")

        logger.info("  Poll %d/%d: %s", attempt, max_attempts, status)
        time.sleep(interval)

    raise TimeoutError(
        f"Upload did not complete after {max_attempts * interval}s (last status: {status})"
    )


def _api_request(req: urllib.request.Request) -> dict:
    """Make an API request, reading the response body even on HTTP errors."""
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
            error = data.get("error", {})
            msg = error.get("message") or error.get("code") or body
        except (json.JSONDecodeError, AttributeError):
            msg = body
        raise RuntimeError(f"TikTok API error (HTTP {e.code}): {msg}") from e


def _compute_chunk_size(video_size: int) -> int:
    """Compute appropriate chunk size for a given video size."""
    if video_size <= _MIN_CHUNK:
        return video_size  # Single chunk for small files
    return min(_DEFAULT_CHUNK, _MAX_CHUNK)
