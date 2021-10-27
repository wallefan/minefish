# Yes, I use both http.client and urllib.  http.client is for downloading, urllib is for one-off API calls to a bunch
# of different servers.
from swordfish_launcher.gui import SwordfishLauncher

if __name__ == '__main__':
    __package__='swordfish_launcher'
    SwordfishLauncher().mainloop()
