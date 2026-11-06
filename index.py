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
    
    # 1. Ping oEmbed endpoint
    try:
        requests.get(
            f"https://www.instagram.com/api/v1/oembed/?url={clean_url}/",
            headers=IG_HEADERS,
            timeout=8
        )
    except Exception:
        pass

    # 2. Extract OpenGraph and CDN link patterns from post HTML
    try:
        page = requests.get(f"{clean_url}/", headers=IG_HEADERS, timeout=10)
        
        og_match = re.search(r'property="og:video"\s+content="([^"]+)"', page.text)
        if og_match:
            return og_match.group(1).replace("&amp;", "&")

        alt_match = re.search(r'content="([^"]+)"\s+property="og:video"', page.text)
        if alt_match:
            return alt_match.group(1).replace("&amp;", "&")

        cdn_match = re.search(r'(https://[^"\\]+cdninstagram\.com/[^"\\]+\.mp4[^"\\]*)', page.text)
        if cdn_match:
            clean_cdn = cdn_match.group(1).encode().decode('unicode-escape')
            return clean_cdn.replace("&amp;", "&")
    except Exception as e:
        print(f"Extraction error: {e}")

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
