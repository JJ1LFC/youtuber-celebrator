#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S%z'
)

YOUTUBE_API_KEY: Optional[str] = os.getenv("YOUTUBE_API_KEY")
DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")
API_BASE_URL: str = "https://www.googleapis.com/youtube/v3"


def load_json(filepath: str) -> Dict[str, Any]:
    """Load JSON data from a file.

    If the file is empty or invalid, return an empty dict.
    """
    logging.info(f"Loading JSON from {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
            logging.info(f"Loaded JSON: {len(data)} top-level keys")
            return data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.warning(f"Failed to load JSON ({e}), returning empty dict")
        return {}


def save_json(data: Dict[str, Any], filepath: str) -> None:
    """Save a dict as JSON to a file."""
    logging.info(f"Saving JSON to {filepath}")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info("JSON saved successfully")


def fetch_channel_info(channel_id: str, desc: str) -> Dict[str, Any]:
    """Fetch subscriber count & timestamp for a channel."""
    logging.info(f"Fetching channel info for {desc} ({channel_id})")
    url = f"{API_BASE_URL}/channels"
    params = {"part": "statistics", "id": channel_id, "key": YOUTUBE_API_KEY}
    resp = requests.get(url, params=params)
    timestamp = resp.headers.get("Date", datetime.now(timezone.utc).isoformat())
    data = resp.json()
    items = data.get("items", [])
    if not items:
        logging.warning(f"No channel data for {channel_id}, returning zero subscriber count")
        return {"channel_id": channel_id, "desc": desc, "subscriber_count": 0, "timestamp": timestamp}
    stats = items[0]["statistics"]
    result = {"channel_id": channel_id, "desc": desc, "subscriber_count": int(stats.get("subscriberCount", 0)), "timestamp": timestamp}
    logging.info(f"Fetched subscriber_count={result['subscriber_count']} for {channel_id}")
    return result


def fetch_video_view_count(video_id: str) -> int:
    """Fetch a video's view count."""
    logging.info(f"Fetching view count for video {video_id}")
    url = f"{API_BASE_URL}/videos"
    params = {"part": "statistics", "id": video_id, "key": YOUTUBE_API_KEY}
    resp = requests.get(url, params=params)
    data = resp.json()
    items = data.get("items", [])
    if not items:
        logging.warning(f"No statistics found for video {video_id}, returning zero view count")
        return 0
    stats = items[0]["statistics"]
    count = int(stats.get("viewCount", 0))
    logging.info(f"View count for {video_id}: {count}")
    return count


def fetch_playlist_videos(playlist_id: str, desc: str) -> List[Dict[str, Any]]:
    """Fetch videos in a playlist with stats & timestamp."""
    logging.info(f"Fetching playlist videos for {desc} ({playlist_id})")
    videos: List[Dict[str, Any]] = []
    url = f"{API_BASE_URL}/playlistItems"
    params = {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": 50, "key": YOUTUBE_API_KEY}

    while True:
        resp = requests.get(url, params=params)
        timestamp = resp.headers.get("Date", datetime.now(timezone.utc).isoformat())
        data = resp.json()
        for item in data.get("items", []):
            vid = item["contentDetails"]["videoId"]
            title = item["snippet"].get("title", "")
            view_count = fetch_video_view_count(vid)
            videos.append({
                "video_id": vid,
                "title": title,
                "url": f"https://youtu.be/{vid}",
                "view_count": view_count,
                "timestamp": timestamp,
                "playlist_id": playlist_id,
                "playlist_desc": desc,
            })
            time.sleep(1)
        next_token = data.get("nextPageToken")
        if not next_token:
            break
        params["pageToken"] = next_token
    logging.info(f"Fetched {len(videos)} videos from playlist {playlist_id}")
    return videos


def send_discord_notification(message: str) -> None:
    """Send a message to Discord via webhook."""
    logging.info(f"Sending Discord notification: {message}")
    if not DISCORD_WEBHOOK_URL:
        logging.warning("DISCORD_WEBHOOK_URL not set, skipping notification")
        return
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    logging.info("Discord notification sent")
    # Wait 1 second after Discord notification to avoid rate limiting
    time.sleep(1)


def compare_and_notify(prev: Dict[str, Any], curr_ch: List[Dict[str, Any]], curr_vd: List[Dict[str, Any]], cfg: Dict[str, Any]) -> None:
    """Compare previous vs current and notify threshold, added/removed items."""
    logging.info("Starting comparison and notification step")
    prev_ch_map = {c["channel_id"]: c["subscriber_count"] for c in prev.get("channels", [])}
    prev_vid_map = {v["video_id"]: v["view_count"] for v in prev.get("videos", [])}

    prev_ids = set(prev_vid_map.keys())
    curr_ids = {v["video_id"] for v in curr_vd}

    # Detect newly added videos
    for vid in curr_ids - prev_ids:
        vd = next(v for v in curr_vd if v["video_id"] == vid)
        send_discord_notification(
            f"➕ New video detected: [{vd['playlist_desc']}] '{vd['title']}' ({vid}) is now monitored. Current views: {vd['view_count']}."
        )

    # Detect removed videos
    for vid in prev_ids - curr_ids:
        send_discord_notification(f"🗑️ Video removed: ID {vid} has been excluded from the playlist.")

    # Retrieve threshold lists
    sub_thrs = cfg.get("subscriber_thresholds", [])
    view_thrs = cfg.get("view_thresholds", [])
    if not sub_thrs:
        logging.warning("No 'subscriber_thresholds' in config, skipping subscriber checks")
    if not view_thrs:
        logging.warning("No 'view_thresholds' in config, skipping view count checks")

    # Subscriber threshold notifications
    for ch in curr_ch:
        prev_cnt = prev_ch_map.get(ch["channel_id"], 0)
        curr_cnt = ch["subscriber_count"]
        for thr in sub_thrs:
            if prev_cnt < thr <= curr_cnt:
                send_discord_notification(
                    f"🎉 Milestone reached: Channel '{ch['desc']}' ({ch['channel_id']}) surpassed {thr} subscribers! Current: {curr_cnt}."
                )

    # View count threshold notifications
    for vd in curr_vd:
        prev_v = prev_vid_map.get(vd["video_id"], 0)
        curr_v = vd["view_count"]
        for thr in view_thrs:
            if prev_v < thr <= curr_v:
                send_discord_notification(
                    f"🎉 Milestone reached: Video '{vd['title']}' ({vd['video_id']}) surpassed {thr} views! Current: {curr_v}."
                )
    logging.info("Comparison and notification step completed")


def main() -> None:
    """Main entrypoint: load config, fetch data, compare, and save state."""
    logging.info("=== Script start ===")
    cfg = load_json("config.json")
    out_file = "/app/data/data.json"

    # Load previous state
    prev_data = load_json(out_file)
    # Skip notifications if initial run (no existing data)
    initial_run = not prev_data.get("channels") and not prev_data.get("videos")
    if initial_run:
        logging.info("Initial run detected: skipping notifications.")
        # On initial run, fetch data and save only, no notifications
        curr_ch: List[Dict[str, Any]] = []
        for ch in cfg.get("channels", []):
            curr_ch.append(fetch_channel_info(ch.get("id", ""), ch.get("desc", "")))
            time.sleep(1)
        curr_vd: List[Dict[str, Any]] = []
        for pl in cfg.get("playlists", []):
            curr_vd.extend(fetch_playlist_videos(pl.get("id", ""), pl.get("desc", "")))
        save_json({"channels": curr_ch, "videos": curr_vd}, out_file)
        logging.info("Initial state saved. Exiting.")
        return

    # Normal execution flow
    logging.info("Fetching channel information...")
    curr_ch: List[Dict[str, Any]] = []
    for ch in cfg.get("channels", []):
        curr_ch.append(fetch_channel_info(ch.get("id", ""), ch.get("desc", "")))
        time.sleep(1)
    logging.info("Channel information fetched")

    logging.info("Fetching playlist videos...")
    curr_vd: List[Dict[str, Any]] = []
    for pl in cfg.get("playlists", []):
        curr_vd.extend(fetch_playlist_videos(pl.get("id", ""), pl.get("desc", "")))
    logging.info("Playlist videos fetched")

    compare_and_notify(prev_data, curr_ch, curr_vd, cfg)

    logging.info("Saving new state...")
    save_json({"channels": curr_ch, "videos": curr_vd}, out_file)
    logging.info("=== Script end ===")

if __name__ == "__main__":
    main()

