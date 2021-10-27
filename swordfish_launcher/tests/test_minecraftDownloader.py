from unittest import TestCase
from unittest.mock import patch
import tempfile
from swordfish_launcher.downloader.launchermeta import MinecraftDownloader

class TestMinecraftDownloader(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.downloader = MinecraftDownloader(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_version_url(self):
        with patch.object(self.downloader.client, 'request', side_effect=self.downloader.client.request):
            self.downloader.get_version_url('1.12.2')
            self.downloader.client.request.assert_called_once()
            self.downloader.get_version_url('1.4.7')
            self.downloader.client.request.assert_called_once()

