from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, render_template, flash
import os
import requests
import yt_dlp

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

def is_feed_live(url: str) -> bool:
    """Check if a YouTube feed URL returns a valid response (not 404)."""
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        return response.status_code == 200
    except requests.RequestException:
        return False

@app.route("/")
def index() -> str:
    url = request.args.get('url', type = str)
    if not url:
        return render_template("index.html")

    potential_extractors = ["YoutubeTab", "Youtube"]
    extractor = None
    for potential_extractor in potential_extractors:
        match = yt_dlp.extractor.get_info_extractor(potential_extractor)
        if match.suitable(url):
            extractor = match
            break

    if not extractor:
        flash(f"Unsupported URL: {extractor}", category="post-info")
        return render_template("index.html")

    ydl_opts: yt_dlp._Params = {
        'allowed_extractors': [extractor.IE_NAME],
        'extract_flat': 'in_playlist',
        'extractor_args': {'youtube': {'player_client': ['web']}},
        'no_warnings': True,
        'playlist_items': '0',  # type: ignore[typeddict-item]
        'quiet': True,
        'simulate': 'list_only'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        if "Unsupported URL" in str(e):
            flash(f"Unsupported URL: {url}", category="post-info")
        else:
            print(e, url)
            flash(f"Download Error: {url}", category="post-info")
        return render_template("index.html")

    if not info:
        flash(f"Unsupported URL: {extractor}", category="post-info")
        return render_template("index.html")

    channel_id = info.get("channel_id")
    if not isinstance(channel_id, str):
        flash(f"Could not extract channel ID from: {url}", category="post-info")
        return render_template("index.html")

    data = {}
    if "UC" == channel_id[:2]:
        data.update({
            "video_url": f"https://www.youtube.com/feeds/videos.xml?playlist_id=UULF{channel_id[2:]}",
            "shorts_url": f"https://www.youtube.com/feeds/videos.xml?playlist_id=UUSH{channel_id[2:]}",
            "live_url": f"https://www.youtube.com/feeds/videos.xml?playlist_id=UULV{channel_id[2:]}",
        })
        members_urls = {
            "video_url_members": f"https://www.youtube.com/feeds/videos.xml?playlist_id=UUMF{channel_id[2:]}",
            "shorts_url_members": f"https://www.youtube.com/feeds/videos.xml?playlist_id=UUMS{channel_id[2:]}",
            "live_url_members": f"https://www.youtube.com/feeds/videos.xml?playlist_id=UUMV{channel_id[2:]}"
        }
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = executor.map(is_feed_live, members_urls.values())
        for key, is_live in zip(members_urls.keys(), results):
            if is_live:
                data[key] = members_urls[key]

    webpage_url = info.get("webpage_url")
    data.update({
        "channel_id": channel_id,
        "feed_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
        "webpage_url": webpage_url if isinstance(webpage_url, str) else url
    })

    playlist_id = info.get("id")
    if playlist_id and playlist_id.startswith("PL"):
        data["playlist_id"] = playlist_id
        data["playlist_feed_url"] = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"

    return render_template("index.html", data=data)
