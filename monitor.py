#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
import schedule
from requests_oauthlib import OAuth1


# Environment variables
YOUTUBE_API_KEY: Optional[str]      = os.getenv("YOUTUBE_API_KEY")
DISCORD_WEBHOOK_URL: Optional[str]  = os.getenv("DISCORD_WEBHOOK_URL")
TWITTER_CONSUMER_KEY: Optional[str]        = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET: Optional[str]     = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN: Optional[str]        = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET: Optional[str]       = os.getenv("TWITTER_ACCESS_SECRET")

API_BASE_URL       = "https://www.googleapis.com/youtube/v3"
TWITTER_API_V2_URL = "https://api.twitter.com/2/tweets"


def load_json(filepath: str) -> Dict[str, Any]:
    """Load JSON data from a file."""
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


def fetch_video_view_count(video_id: str) -> int:
    """Fetch a video's view count."""
    logging.info(f"Fetching view count for video {video_id}")
    url = f"{API_BASE_URL}/videos"
    params = {"part": "statistics", "id": video_id, "key": YOUTUBE_API_KEY}
    resp = requests.get(url, params=params)
    items = resp.json().get("items", [])
    if not items:
        logging.warning(f"No statistics for video {video_id}")
        return 0
    count = int(items[0]["statistics"].get("viewCount", 0))
    logging.info(f"View count for {video_id}: {count}")
    return count


def fetch_channel_info(
    channel_id: str,
    desc: str,
    twitter_enabled: bool = False
) -> Dict[str, Any]:
    """Fetch subscriber count & timestamp for a channel."""
    logging.info(f"Fetching channel info for {desc} ({channel_id})")
    url = f"{API_BASE_URL}/channels"
    params = {"part": "snippet,statistics", "id": channel_id, "key": YOUTUBE_API_KEY}
    resp = requests.get(url, params=params)
    timestamp = resp.headers.get("Date", datetime.now(timezone.utc).isoformat())
    data = resp.json().get("items", [])
    item = data[0] if data else {}
    subs = int(item.get("statistics", {}).get("subscriberCount", 0))
    title = item.get("snippet", {}).get("title", desc)
    logging.info(f"Fetched subscriber_count={subs} for {channel_id}")
    return {
        "channel_id": channel_id,
        "title": title,
        "subscriber_count": subs,
        "timestamp": timestamp,
        "twitter_enabled": twitter_enabled
    }


def fetch_playlist_videos(
    playlist_id: str,
    desc: str,
    twitter_enabled: bool = False
) -> List[Dict[str, Any]]:
    """Fetch videos in a playlist with stats & timestamp."""
    logging.info(f"Fetching playlist videos for {desc} ({playlist_id})")
    videos: List[Dict[str, Any]] = []
    url = f"{API_BASE_URL}/playlistItems"
    params = {
        "part": "snippet,contentDetails",
        "playlistId": playlist_id,
        "maxResults": 50,
        "key": YOUTUBE_API_KEY
    }

    while True:
        resp = requests.get(url, params=params)
        timestamp = resp.headers.get("Date", datetime.now(timezone.utc).isoformat())
        items = resp.json().get("items", [])
        for item in items:
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
                "twitter_enabled": twitter_enabled
            })
            time.sleep(1)
        next_token = resp.json().get("nextPageToken")
        if not next_token:
            break
        params["pageToken"] = next_token

    logging.info(f"Fetched {len(videos)} videos from playlist {playlist_id}")
    return videos


def send_discord_notification(message: str) -> None:
    """Send a message to Discord via webhook."""
    logging.info(f"Sending Discord notification: {message}")
    if not DISCORD_WEBHOOK_URL:
        logging.warning("Discord webhook URL not set, skipping notification")
        return
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    logging.info("Discord notification sent")
    time.sleep(1)  # avoid rate limit


def send_twitter_notification(text: str) -> None:
    """Post a tweet via Twitter API v2 using OAuth1.0a user context."""
    if not all([TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        logging.warning("Twitter credentials missing, skipping tweet")
        return
    auth = OAuth1(
        TWITTER_CONSUMER_KEY,
        TWITTER_CONSUMER_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET
    )
    payload = {"text": text}
    resp = requests.post(TWITTER_API_V2_URL, auth=auth, json=payload)
    if resp.status_code == 201:
        logging.info("Tweet posted successfully")
    else:
        logging.error(f"Failed to post tweet: {resp.status_code} {resp.text}")
    time.sleep(1)  # avoid rate limit


def compare_and_notify(
    prev: Dict[str, Any],
    curr_ch: List[Dict[str, Any]],
    curr_vd: List[Dict[str, Any]],
    cfg: Dict[str, Any]
) -> None:
    """Compare previous vs current and notify threshold, added/removed items."""
    logging.info("Starting comparison and notification step")
    prev_ch_map = {c["channel_id"]: c["subscriber_count"] for c in prev.get("channels", [])}
    prev_vid_map = {v["video_id"]: v["view_count"] for v in prev.get("videos", [])}

    # Detect new/removed videos (Discord only)
    prev_ids = set(prev_vid_map.keys())
    curr_ids = {v["video_id"] for v in curr_vd}
    for vid in curr_ids - prev_ids:
        vd = next(v for v in curr_vd if v["video_id"] == vid)
        send_discord_notification(
            f"➕ New video detected: [{vd['playlist_desc']}] '{vd['title']}' ({vid}) monitored.\n{vd['url']}"
        )
    for vid in prev_ids - curr_ids:
        send_discord_notification(
            f"🗑️ Video removed: {vid} removed from playlist."
        )

    # Channel thresholds
    for ch in curr_ch:
        prev_cnt = prev_ch_map.get(ch["channel_id"], 0)
        curr_cnt = ch["subscriber_count"]
        for thr in cfg.get("subscriber_thresholds", []):
            if prev_cnt < thr <= curr_cnt:
                msg = (
                    f"【🎉チャンネル登録 {thr} 人突破🎉】\n\n"
                    f"YouTube チャンネル「{ch['title']}」の登録者数が {thr} 人を突破しました🎉🎉\n\n"
                    f"https://www.youtube.com/channel/{ch['channel_id']}"
                )
                send_discord_notification(msg)
                if ch.get("twitter_enabled"):
                    send_twitter_notification(msg)

    # Video thresholds
    for vd in curr_vd:
        prev_v = prev_vid_map.get(vd["video_id"], 0)
        curr_v = vd["view_count"]
        for thr in cfg.get("view_thresholds", []):
            if prev_v < thr <= curr_v:
                msg = (
                    f"【🎉再生回数 {thr} 回突破🎉】\n\n"
                    f"歌動画「{vd['title']}」の総再生回数が {thr} 回を突破しました🎉🎉\n\n"
                    f"{vd['url']}"
                )
                send_discord_notification(msg)
                if vd.get("twitter_enabled"):
                    send_twitter_notification(msg)

    logging.info("Comparison and notification step completed")


def main() -> None:
    cfg = load_json("config.json")
    level_name = cfg.get("log_level", "WARNING").upper()
    numeric_level = getattr(logging, level_name, logging.WARNING)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        force=True
    )
    logging.info(f"=== Script start (log_level={level_name}) ===")

    out_file = "/app/data/data.json"
    prev_data = load_json(out_file)

    # Initial run
    if not prev_data.get("channels") and not prev_data.get("videos"):
        logging.info("Initial run: skipping notifications.")
        curr_ch: List[Dict[str, Any]] = [
            fetch_channel_info(ch['id'], ch['desc'], ch.get('twitter_enabled', False))
            for ch in cfg.get("channels", [])
        ]
        time.sleep(1)
        curr_vd: List[Dict[str, Any]] = []
        for pl in cfg.get("playlists", []):
            curr_vd.extend(fetch_playlist_videos(pl['id'], pl['desc'], pl.get('twitter_enabled', False)))
        save_json({"channels": curr_ch, "videos": curr_vd}, out_file)
        logging.info("Initial state saved.")
        return

    # Normal execution
    curr_ch = [
        fetch_channel_info(ch['id'], ch['desc'], ch.get('twitter_enabled', False))
        for ch in cfg.get("channels", [])
    ]
    time.sleep(1)
    curr_vd: List[Dict[str, Any]] = []
    for pl in cfg.get("playlists", []):
        curr_vd.extend(fetch_playlist_videos(pl['id'], pl['desc'], pl.get('twitter_enabled', False)))

    compare_and_notify(prev_data, curr_ch, curr_vd, cfg)
    save_json({"channels": curr_ch, "videos": curr_vd}, out_file)
    logging.info("=== Script end ===")


if __name__ == "__main__":
    schedule.every().hour.at(":00").do(main)
    main()
    while True:
        schedule.run_pending()
        time.sleep(1)

