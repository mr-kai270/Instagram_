import re
import requests
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

IG_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "X-IG-App-ID": "936619743392459",
    "Accept": "*/*",
    "Sec-Fetch-Mode": "cors"
}

def extract_direct_video_url(post_url: str):
    clean_url = post_url.split("?")[0].rstrip("/")
    shortcode_match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', clean_url)
    if not shortcode_match:
        return None
    shortcode = shortcode_match.group(1)

    # Strategy 1: Fast public proxy service (handles residential IP rotation)
    try:
        api_endpoint = f"https://api.vkrdown.com/insta/?url=https://www.instagram.com/reel/{shortcode}/"
        res = requests.get(api_endpoint, timeout=10)
        if res.status_code == 200:
            data = res.json()
            # Most scrapers return direct download URL under 'url' or 'data.url'
            video = data.get("url") or (data.get("data", [{}])[0].get("url") if isinstance(data.get("data"), list) else None)
            if video:
                return video
    except Exception:
        pass

    # Strategy 2: Direct Embed/GraphQL fetch with mobile user-agent fallback
    try:
        mobile_headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
        embed_res = requests.get(embed_url, headers=mobile_headers, timeout=10)
        
        # Instagram embeds still contain video source links in captioned mode
        video_match = re.search(r'class="EmbeddedVideo"\s+src="([^"]+)"', embed_res.text)
        if video_match:
            return video_match.group(1).replace("&amp;", "&")
            
        cdn_match = re.search(r'https://[^"\\\\]+cdninstagram\.com/[^"\\\\]+\.mp4[^"\\\\]*', embed_res.text)
        if cdn_match:
            return cdn_match.group(0).encode().decode('unicode-escape').replace("&amp;", "&")
    except Exception as e:
        print(f"Fallback extraction failed: {e}")

    return None

@app.route('/api/stream', methods=['GET'])
def proxy_stream():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing video URL parameter"}), 400

    stream_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.instagram.com/"
    }

    try:
        req = requests.get(video_url, headers=stream_headers, stream=True, timeout=15)
        return Response(
            stream_with_context(req.iter_content(chunk_size=65536)),
            content_type=req.headers.get('content-type', 'video/mp4'),
            headers={
                "Content-Disposition": "attachment; filename=instagram-video.mp4",
                "Accept-Ranges": "bytes"
            }
        )
    except Exception as e:
        return jsonify({"error": f"Streaming failed: {str(e)}"}), 500

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def index_handler(path):
    if request.method == 'GET':
        return jsonify({"status": "API is online"})

    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()

    if not url or 'instagram.com' not in url:
        return jsonify({'error': 'Please enter a valid Instagram reel or post link.'}), 400

    direct_url = extract_direct_video_url(url)
    if not direct_url:
        return jsonify({
            'error': 'Video stream not found. Instagram may have throttled the server IP, or the post is private.'
        }), 404

    return jsonify({
        'direct_url': direct_url,
        'proxy_url': f"/api/stream?url={requests.utils.quote(direct_url)}"
    })
