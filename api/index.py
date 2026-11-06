import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

# 1. This variable MUST be named exactly "app" at the top level
app = Flask(__name__)
CORS(app)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    if request.method == 'GET':
        return jsonify({"status": "API is online"})

    data = request.get_json(silent=True) or {}
    url = data.get('url', '')

    if not url:
        return jsonify({'error': 'Please provide a valid URL'}), 400

    # Your extraction logic here
    return jsonify({'message': f'Received URL: {url}'})

# 2. DO NOT include app.run() here; Vercel handles invocation automatically
