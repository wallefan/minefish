__package__='swordfish_launcher.gui.settings'

from . import SettingsDialog
import configparser
import tkinter

if __name__=='__main__':
    config=configparser.ConfigParser()
    for _ in range(2):
        root=tkinter.Tk()
        SettingsDialog(root, config).pack()
        root.mainloop()