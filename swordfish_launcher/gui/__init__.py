import configparser
import http.client
import json
import tkinter
import tkinter.ttk as ttk

from .pack_selector import ScrollableList

MESSAGES = {
    'Invalid credentials. Invalid username or password.': 'Wrong password',
    'Invalid credentials. Account migrated, use email as username.': 'Not your username, your email address',
    'Invalid credentials.': 'Too many failed login attempts'
}

class SwordfishLauncher(tkinter.Tk):
    def __init__(self):
        super().__init__()
        self.config=configparser.ConfigParser()
        try:
            self.config.read('swordfish.ini')
        except FileNotFoundError:
            pass
        self.configure(width=640, height=480)
        self._authclient=None
        self._authdialog=None
        self._settings_dialog=None

        self.paned_window = tkinter.PanedWindow(self)
        self.paned_window.pack(expand=True, fill='both')
        self.pack_list_widget = ScrollableList(self.paned_window)
        self.paned_window.add(self.pack_list_widget, sticky='nws')
        self.center_pane = tkinter.Canvas(self.paned_window)
        self.paned_window.add(self.center_pane, sticky='nsew')

        menubar = tkinter.Menu(self)
        self.configure(menu=menubar)
        menu_launcher = tkinter.Menu(menubar, tearoff=0)
        menu_launcher.add_command(label='Options...', command=self.settings_dialog)
        menu_launcher.add_command(label='Help (trust me on this)...')

        menubar.add_cascade(menu=menu_launcher, label='Launcher')

        self.authenticate()

    def authenticate(self, user=None):
        if self._authclient is None:
            self._authclient = http.client.HTTPSConnection('authserver.mojang.com')
        if not self.config.has_section('Auth'):
            self.config.add_section('Auth')
            if user:
                self.config['Auth']['Last User'] = user
            self.show_auth_dialog()
            return
        auth = self.config['Auth']
        if user:
            auth['Last User'] = user
        else:
            user = auth.get('Last User')
            if not user:
                self.show_auth_dialog()
                return
        existing_token = self._get_token(user)
        if not existing_token:
            self.show_auth_dialog()
            return
        data = json.dumps(dict(accessToken=existing_token, clientToken=auth['Installation UUID']))
        headers = {'Content-Type': 'application/json', 'User-Agent': 'Swordfish Launcher'}
        self._authclient.request('POST', '/validate', data, headers)
        with self._authclient.getresponse() as r:
            if r.code == 204:
                # the token is valid.
                self._authclient.close()
                self._authclient = None
                return
            elif r.code == 403:
                # the token is invalid and we need to refresh it.
                # The server has sent us JSON telling us this.  We do not care about that JSON.
                # However, there is a bug in http.client that forces us to read it.
                # If Connection is set to Keep-Alive and response.close() is called
                # before the entire response has been read, the connection object will
                # be put into an unusable state.
                r.read()
            else:
                raise ValueError('Expected 204 or 403 from auth validate, but server returned %d'%r.code)

        # if we got this far, the token is expired.  Let's get a new one.
        self._authclient.request('POST', '/refresh', data, headers)
        with self._authclient.getresponse() as r:
            response = json.load(r)
        if r.code == 200:
            self.process_authserver_response(response, user)
            return
        elif r.code == 403:
            self.show_auth_dialog()
        else:
            raise ValueError(r.code, response)

    def _get_token(self, user):
        if not self.config.has_section('Tokens'):
            self.config.add_section('Tokens')
            return None
        return self.config['Tokens'].get(user)

    def show_auth_dialog(self):
        if self._authdialog is not None and self._authdialog.winfo_exists():
            self._authdialog.bell()
        else:
            self._authdialog = self._create_authdialog()

    def _create_authdialog(self):
        """Create an auth dialog as a child window of self, and return the window.
        Tell this function which user we are logging in as (i.e. the default content of the Username: field)
        by setting self.config['Auth']['Last User'].
        """
        auth = self.config['Auth']
        dialog = tkinter.Toplevel(self)
        tkinter.Label(dialog, text='Username:').grid(row=0, column=0)
        userbox = tkinter.Entry(dialog)
        last_user = auth.get('Last User')
        if last_user:
            userbox.insert(0, last_user)
            userbox.select_range(0,len(last_user))
        userbox.grid(row=0, column=1)
        tkinter.Label(dialog, text='Password:').grid(row=1, column=0)
        passbox = tkinter.Entry(dialog, show='\u2022')  # \u2022 is a bullet point (commonly used for passwords)
        passbox.grid(row=1, column=1)
        def callback(evt=None):
            user = auth['Last User'] = userbox.get()
            d=dict(username=userbox.get(), password=passbox.get())
            if 'Installation UUID' in auth:
                d['clientToken']=auth['Installation UUID']
            self._authclient.request('POST','/authenticate',json.dumps(d), {'Content-Type':'application/json','User-Agent':'Swordfish Launcher'})
            with self._authclient.getresponse() as resp:
                data = json.load(resp)
                code = resp.code
            if code == 200:
                dialog.destroy()
                self.process_authserver_response(data, user)
            else:
                message = data['errorMessage']
                if message == 'Invalid credentials. Account migrated, use email as username.':
                    tkinter.messagebox.showwarning('Login Failed','Your email address, silly!', parent=dialog)
                    userbox.delete(0, -1)
                else:
                    tkinter.messagebox.showwarning('Login Failed', MESSAGES.get(message, message), parent=dialog)

        tkinter.Button(dialog, text='Log In', command=callback).grid(row=2, column=0, columnspan=2)
        passbox.bind('<Return>', callback)
        return dialog

    def process_authserver_response(self, data: dict, user):
        print(data)
        if not self.config.has_section('Tokens'):
            self.config.add_section('Tokens')

        self.config['Auth']['Installation UUID']=data['clientToken']
        self.config['Tokens'][user] = data['accessToken']
        self.save_config()
        if self._authclient:
            # No point leaving the authserver connection open after we're done with it.
            self._authclient.close()
            self._authclient = None

        from ..login import get_minecraft_profile
        print(get_minecraft_profile(data['accessToken']))

    def save_config(self):
        with open('swordfish.ini', 'w', encoding='utf8') as f:
            self.config.write(f)

    def settings_dialog(self):
        if self._settings_dialog is not None and self._settings_dialog.winfo_exists():
            self._settings_dialog.bell()
            return
        from .settings import SettingsDialog
        self._settings_dialog = tkinter.Toplevel()
        dlg=SettingsDialog(self._settings_dialog, self.config)
        dlg.pack(expand=True, fill='both')
        def ok():
            self.save_config()
            self._settings_dialog.destroy()
            self._settings_dialog = None
        tkinter.Button(self._settings_dialog, text='OK', command=ok).pack()
        #tkinter.Button(dlg, text='Save', command=self.save_config).pack()
        self._settings_dialog.minsize(500,250)


    def setup(self):
        self.config.add_section('Auth')