import configparser
import tkinter
import tkinter.ttk
import tkinter.filedialog
import tkinter.messagebox
from .util import BaseDialog
from ..util import bind_tooltip

class General(BaseDialog):
    def __init__(self, master, config: configparser.ConfigParser):
        super().__init__(master, config)
        self.add_checkbutton("Use error dialogs for all errors", "use messageboxes for everything", default=True).pack()
        self.secret_button = tkinter.Button(self, text='Super Secret Settings...', command=self.create_super_secret_dialog)
        self.secret_button.place(x=500, y=100)  # with the default size of the window this will be offscreen.

    def create_super_secret_dialog(self):
        from .secret import Secret
        self.master.panels['Secret'] = Secret(self.master, self.config.parser)
        self.master.panel_switcher.insert(999, 'Secret')
        #self.master.panel_switcher.select_clear(0,9999)
        #self.master.panel_switcher.selection_set(0,0)
        #self.master.switch_panels()
        self.secret_button.destroy()


class Advanced(BaseDialog):
    def __init__(self, master, config):
        super().__init__(master, config)
        java_row, self.java_var = self.add_textbox("Java executable", 'javapath', 'java')
        tkinter.Button(self, text='Auto detect', command=self._autodetect_java).grid(row=java_row, column=2)
        tkinter.Button(self, text='Browse', command=self._browse_for_java).grid(row=java_row, column=3)
        self.add_checkbutton('test', default=False).grid(row=1, sticky='w')

    def _browse_for_java(self):
        path = tkinter.filedialog.askopenfilename(master=self, initialfile=self.java_var.get())
        if path:
            self.java_var.set(path)
            self.config['javapath']=path

    def _autodetect_java(self):
        tkinter.messagebox.showwarning('Not Implemented', "I haven't finished Java autodetection yet")

    def _test_java(self):
        pass

    def add_textbox(self, description_text, cfgpath, default, tooltip=None):
        label = tkinter.Label(self, text=description_text)
        label.grid(column=0, sticky='w')
        var = tkinter.StringVar()
        row = label.grid_info()['row']
        entry = tkinter.ttk.Entry(self, textvariable=var)
        entry.grid(row=row, column=1, sticky='w')
        if tooltip:
            bind_tooltip(entry, tooltip)
        callback = self.monitor_variable(var, cfgpath, default)
        entry.bind('<Return>', callback)
        return row, var
