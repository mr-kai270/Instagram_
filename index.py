import re
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_instagram_direct_url(url: str):
    clean_url = url.split("?")[0].rstrip("/") + "/?__a=1&__d=dis"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Mode": "cors"
    }

    response = requests.get(clean_url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        try:
            data = response.json()
            items = data.get("graphql", {}).get("shortcode_media") or data.get("items", [{}])[0]
            
            # Check for video version
            if "video_versions" in items:
                return items["video_versions"][0]["url"]
            elif "video_url" in items:
                return items["video_url"]
        except Exception:
            pass

    # Fallback: Scrape metadata tags directly from the web document
    page_res = requests.get(url, headers=headers, timeout=10)
    video_match = re.search(r'property="og:video"\s+content="([^"]+)"', page_res.text)
    if video_match:
        return video_match.group(1).replace("&amp;", "&")

    return None

@app.route('/api/index', methods=['POST', 'GET'])
def handler():
    if request.method == 'GET':
        return jsonify({"status": "API is online"})
        
    body = request.get_json(silent=True) or {}
    url = body.get('url')

    if not url or 'instagram.com' not in url:
        return jsonify({'error': 'Please enter a valid Instagram URL.'}), 400

    try:
        video_url = get_instagram_direct_url(url)
        if not video_url:
            return jsonify({
                'error': 'Could not extract direct media. The reel may be private or rate-limited.'
            }), 404

        return jsonify({'video_url': video_url})
    except Exception as e:
        return jsonify({'error': f'Server extraction error: {str(e)}'}), 500