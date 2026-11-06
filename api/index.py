import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def extract_instagram_video(url: str):
    clean_url = url.split("?")[0].rstrip("/")
    # Extract the shortcode (e.g. from /reel/C12345/ or /p/C12345/)
    match = re.search(r'/(?:reel|p|tv)/([A-Za-z0-9_-]+)', clean_url)
    if not match:
        return None
    shortcode = match.group(1)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-IG-App-ID": "936619743392459",  # Required public web client ID
        "Accept": "*/*",
        "Sec-Fetch-Mode": "cors"
    }

    # Query Instagram's public web graphql endpoint
    api_url = f"https://www.instagram.com/api/v1/oembed/?url=https://www.instagram.com/p/{shortcode}/"
    
    try:
        # Fallback to direct HTML og:video tag if API blocks
        page = requests.get(f"https://www.instagram.com/p/{shortcode}/", headers=headers, timeout=10)
        og_match = re.search(r'property="og:video"\s+content="([^"]+)"', page.text)
        if og_match:
            return og_match.group(1).replace("&amp;", "&")
    except Exception:
        pass
    
    return None

@app.route('/api', methods=['POST'])
def api_handler():
    body = request.get_json(silent=True) or {}
    url = body.get('url', '')
    if not url:
        return jsonify({'error': 'Please provide a valid URL'}), 400

    video_url = extract_instagram_video(url)
    if not video_url:
        return jsonify({'error': 'Unable to extract video. It might be private or blocked.'}), 404

    return jsonify({'video_url': video_url})



        
        return jsonify({'video_url': video_url})
    except Exception as e:
        return jsonify({'error': f'Server extraction error: {str(e)}'}), 500
