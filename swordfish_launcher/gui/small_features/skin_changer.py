import tkinter
import http.client
import pathlib
import os

class SkinChanger(tkinter.Frame):
    def __init__(self, parent, player_uuid):
        super().__init__(parent)
        self.player_uuid=player_uuid
        self.client = http.client.HTTPSConnection('api.mojang.com')
        self.list_pane = tkinter.Frame(self)
        self.list_pane.pack(expand=True, fill='xy')
        self.preview_pane = tkinter.Label(self)
        self.preview_pane.pack(expand=False, fill='xy')


    def upload_skin(self, skin_file: pathlib.Path, model=''):
        self.client.putrequest('PUT', '/user/profiles/%s/skin' % self.player_uuid)
        boundary = os.urandom(8)
        self.client.putheader('Content-Type', 'multipart/form-data; boundary=<boundary>')
        self.client.putheader('')

