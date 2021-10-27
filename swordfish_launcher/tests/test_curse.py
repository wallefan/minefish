from unittest import TestCase
from swordfish_launcher.downloader.third_party.curse import CurseModpack


class TestCurseModpack(TestCase):
    def test_search(self):
        pack = CurseModpack.search('unhinged')[0]
        pack._getimage('icon')
