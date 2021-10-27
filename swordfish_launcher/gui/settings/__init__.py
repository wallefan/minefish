import tkinter
import configparser
from .general import General, Advanced

class SettingsDialog(tkinter.PanedWindow):
    def __init__(self, master, config: configparser.ConfigParser = None):
        super().__init__(master)
        self.panel_switcher = tkinter.Listbox(self)
        self.add(self.panel_switcher, sticky='nsw')

        self.panels = {cls.__name__: cls(self, config) for cls in (General, Advanced)}

        self.active_panel = None
        self.panel_switcher.insert(0, *self.panels)
        self.panel_switcher.bind('<<ListboxSelect>>', self.switch_panels)
        self.panel_switcher.select_set(0)
        self.switch_panels()

    def switch_panels(self, evt=None):
        if self.active_panel:
            self.remove(self.active_panel)
        self.active_panel = self.panels[self.panel_switcher.selection_get()]
        self.add(self.active_panel, sticky='nsew')
