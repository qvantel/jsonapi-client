import json
import os
import time
import requests
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

NB_CLIENT_ID = os.environ['NB_CLIENT_ID']
NB_CLIENT_SECRET = os.environ['NB_CLIENT_SECRET']
NB_REDIRECT_URI = os.environ.get('NB_REDIRECT_URI', 'http://localhost:8080/callback')
NB_SLUG = os.environ['NB_SLUG']
TOKEN_FILE = 'token.json'

AUTH_URL = f"https://{NB_SLUG}.nationbuilder.com/oauth/authorize"
TOKEN_URL = f"https://{NB_SLUG}.nationbuilder.com/oauth/token"

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        code = query.get('code')
        if code:
            self.server.auth_code = code[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization complete! You can close this window.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code.")
    def log_message(self, format, *args):
        return

def open_browser_for_auth():
    params = {
        'client_id': NB_CLIENT_ID,
        'redirect_uri': NB_REDIRECT_URI,
        'response_type': 'code',
    }
    auth_url = AUTH_URL + '?' + urllib.parse.urlencode(params)
    webbrowser.open(auth_url)
    print("Browser opened for login...")

def wait_for_auth_code():
    httpd = HTTPServer(('localhost', 8080), OAuthHandler)
    httpd.handle_request()
    return httpd.auth_code

def exchange_code_for_tokens(code):
    data = {
        'client_id': NB_CLIENT_ID,
        'client_secret': NB_CLIENT_SECRET,
        'redirect_uri': NB_REDIRECT_URI,
        'grant_type': 'authorization_code',
        'code': code,
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    tokens = resp.json()
    tokens['timestamp'] = int(time.time())
    save_tokens(tokens)
    return tokens

def refresh_access_token(refresh_token):
    data = {
        'client_id': NB_CLIENT_ID,
        'client_secret': NB_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    tokens = resp.json()
    tokens['timestamp'] = int(time.time())
    save_tokens(tokens)
    return tokens

def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f)

def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)

def token_expired(tokens, buffer_seconds=60):
    expires_in = tokens.get('expires_in', 0)
    timestamp = tokens.get('timestamp', 0)
    return time.time() > (timestamp + expires_in - buffer_seconds)

def get_auth_kwargs():
    tokens = load_tokens()

    if not tokens:
        open_browser_for_auth()
        code = wait_for_auth_code()
        tokens = exchange_code_for_tokens(code)

    elif token_expired(tokens):
        print("Access token expired — refreshing...")
        tokens = refresh_access_token(tokens['refresh_token'])

    return {
        "headers": {
            "Authorization": f"Bearer {tokens['access_token']}",
            "Content-Type": "application/json"
        }
    }
