try:
    if __package__ is None: raise NameError
except NameError:
    __package__ = 'swordfish_launcher.login'

import http.server
import webbrowser
import urllib.parse
import urllib.request
import urllib.error
import json
from ..minefish import USER_AGENT


class _LoginRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if 'code' in query:
            self.server.access_code = query['code'][0]
            self.send_response(200)
            html = """<html><h1>Sign-in Complete</h1><p>You can close this window now.</p></html>"""
            html = html.encode('utf8')
            self.send_header('Content-Type', 'text/html; charset=utf8')
            self.send_header('Content-Length', str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            # ugly but it works.
            self.server._BaseServer__shutdown_request = True


def json_request(url, data):
    req = urllib.request.Request(url,
                                 data=json.dumps(data).encode('utf8'),
                                 headers={'Content-Type': 'application/json',
                                          'Accept': 'application/json',
                                          'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode(resp.headers.get_content_charset('utf8')))


def do_browser_handoff():
    """Opens the user's default browser to sign into a Microsoft account, and returns an access code which can be used
    to authenticate to Live.com.
    """
    server = http.server.HTTPServer(('localhost', 35117), _LoginRequestHandler)
    webbrowser.open('https://login.live.com/oauth20_authorize.srf?response_type=code&client_id=d1fc4364-42c4-4b20'
                    f'-8ea7-3cba459ea92b&redirect_uri=http%3A%2F%2Flocalhost%3A{server.server_port}&scope=XboxLive.signin'
                    '%20offline_access')
    # request handler will stop the serve_forever() loop as soon as it gets an access code.
    server.serve_forever()
    return server.access_code


def live_login(browser_code):
    """Take the access code from the browser handoff and turn it into a Live.com access token, completing the login sequence.
    """
    with urllib.request.urlopen(
            urllib.request.Request('https://login.live.com/oauth20_token.srf', data=urllib.parse.urlencode(
                    {'client_id': 'd1fc4364-42c4-4b20-8ea7-3cba459ea92b',
                     'code': browser_code,
                     'grant_type': 'authorization_code',
                     'redirect_uri': 'http://localhost:35117'
                     }).encode('utf8'), headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            })) as resp:
        data = json.loads(resp.read().decode(resp.headers.get_content_charset('utf8')))
    print('LIVE.COM LOGIN SUCCESS')
    print(data)
    return data['access_token']

def xbl_login(access_token):
    """Takes a Live.com access token and logs into XBox Live with it, returning a 2-tuple (xbl_token, user_hash)."""
    xbl_response = json_request('https://user.auth.xboxlive.com/user/authenticate',
                                {
                                    'Properties': {
                                        'AuthMethod': 'RPS',
                                        'SiteName': 'user.auth.xboxlive.com',
                                        'RpsTicket': 'd=' + access_token
                                    },
                                    'RelyingParty': 'http://auth.xboxlive.com',
                                    'TokenType': 'JWT'
                                })
    print('XBL LOGIN SUCCESS')
    print(xbl_response)
    return xbl_response['Token'], xbl_response['DisplayClaims']['xui'][0]['uhs']

def xsts_login(xbl_token):
    """Takes the XBL token from xbl_login() and authenticates to XSTS, completing the XBox Live login.
    Returns a 2-tuple (xsts_token, user_hash).  The user_hash returned should match the one from xbl_login.
    """
    xsts_login_response = json_request('https://xsts.auth.xboxlive.com/xsts/authorize',
                                       {
                                           'Properties': {
                                               'SandboxId': 'RETAIL',
                                               'UserTokens': [xbl_token],
                                           },
                                           'RelyingParty': 'rp://api.minecraftservices.com/',
                                           'TokenType': 'JWT'
                                       })
    print('XSTS LOGIN SUCCESS')
    print(xsts_login_response)
    return xsts_login_response['Token'], xsts_login_response['DisplayClaims']['xui'][0]['uhs']

def minecraft_login(user_hash, xsts_token):
    """Log into Minecraft via XBox Live and return a JWT token that can be passed directly to the game
    and/or used for other API calls.
    """
    minecraft_login_response = json_request(
        'https://api.minecraftservices.com/authentication/login_with_xbox',
        {'identityToken': f'XBL3.0 x={user_hash};{xsts_token}'})
    return minecraft_login_response['access_token']

def login_sequence_quiet():
    browser_token = do_browser_handoff()
    print('Browser handoff complete.')
    live_token = live_login(browser_token)
    print('Successfully logged into Live.com.')
    xbl_token, user_hash = xbl_login(live_token)
    print('Authenticated to XBox Live.')
    xsts_token, user_hash = xsts_login(xbl_token)
    print('Authenticated to XSTS and logged into XBox Live.')
    return minecraft_login(user_hash, xsts_token)


if __name__ == '__main__':
    __package__ = 'swordfish_launcher.login'
    from . import get_minecraft_profile, owns_minecraft
    minecraft_token = login_sequence_quiet()
    print('Successfully logged into Minecraft.')
    if owns_minecraft(minecraft_token):
        print('Account owns Minecraft.  Here are the profile details:')
        print(get_minecraft_profile(minecraft_token))
    else:
        print('Account does not own Minecraft.')

