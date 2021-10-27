import tkinter
import tkinter.ttk

class SetupWizardDialog(tkinter.Frame):
    def __init__(self, parent):
        super().__init__(parent, width=800, height=600)
        self.bottom_frame = tkinter.Frame(self)
        self.bottom_frame.pack(side='bottom', expand=1, fill='x', padx=3)
        tkinter.ttk.Button(self.bottom_frame, text='Next', command=self.next).pack(side='right', padx=3)
        tkinter.ttk.Button(self.bottom_frame, text='Back', command=self.prev).pack(side='right', padx=3)

    def next(self):
        pass

    def prev(self):
        pass


if __name__=='__main__':
    tk=tkinter.Tk()
    dlg=SetupWizardDialog(tk)
    dlg.pack(expand=1, fill='both')
    import pkgutil
    img = tkinter.PhotoImage(master=tk, data=pkgutil.get_data('swordfish_launcher.gui', 'sunflower.gif'))
    tkinter.Label(dlg, image=img).pack()
    tk.mainloop()


