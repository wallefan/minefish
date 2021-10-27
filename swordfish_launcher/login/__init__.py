import urllib.request
import json


def get_minecraft_profile(minecraft_token):
    """Return a JSON object (a Python dict) containing information about the user in the given minecraft token,
    such as the player UUID, the in-game name (IGN), and a list of skins the user has uploaded.

    This will fail with a 404 Not Found error if the minecraft token passed is associated with a Microsoft account that
    does not own Minecraft.
    """
    with urllib.request.urlopen(urllib.request.Request('https://api.minecraftservices.com/minecraft/profile',
                                                       headers={'Authorization': 'Bearer ' + minecraft_token,
                                                                'Accept': 'application/json'})) as resp:
        return json.loads(resp.read().decode(resp.headers.get_content_charset('utf8')))


def owns_minecraft(minecraft_token) -> bool:
    """It is possible, for some reason, to log into Minecraft, and get a valid Minecraft JWT token,
    from a Microsoft account that does not actually own the game.  Calling get_minecraft_profile() with such a token
    will result in a 404.  This function will contact the Minecraft API and determine whether or not the account
    associated with the given token owns Minecraft.

    This will fail with a 400 Bad Request error if passed a Minecraft token returned from Yggdrasil (the legacy
    Mojang authentication system that takes an email address and password) rather than XBox Live.
    """
    with urllib.request.urlopen(urllib.request.Request('https://api.minecraftservices.com/entitlements/mcstore',
                                                       headers={'Authorization': 'Bearer ' + minecraft_token})) as resp:
        data = json.loads(resp.read().decode(resp.headers.get_content_charset('utf8')))
    return any(item['name'] == 'game_minecraft' for item in data['items'])

