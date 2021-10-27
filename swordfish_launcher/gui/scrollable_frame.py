import tkinter
import tkinter.ttk


class ScrollableFrame(tkinter.Frame):
    def __init__(self, parent, *args, scrollbar_side='left', **kw):
        super().__init__(parent, *args, **kw)
        self.scrollbar = tkinter.Scrollbar(parent)
        canvas = tkinter.Canvas(self, yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=canvas.yview)
        self.scrollable_region = tkinter.Frame(canvas)
        _frame_id = canvas.create_window(0, 0, window=self.scrollable_region, anchor='nw')
        self.scrollable_region.bind('<Configure>', lambda evt: canvas.config(scrollregion=canvas.bbox('all')))
        self.scrollbar.pack(side=scrollbar_side, fill='y')
        canvas.pack(side=scrollbar_side, expand=True, fill='both')
        self.yview_scroll = canvas.yview_scroll
        canvas.bind('<Enter>', self._mouse_in)
        canvas.bind('<Leave>', self._mouse_out)

    def _mouse_in(self, evt2):
        print('MOUSE IN')
        self.bind_all('<Button-4>', lambda evt: self.yview_scroll(-120, 'units'))
        self.bind_all('<Button-5>', lambda evt: self.yview_scroll(120, 'units'))
        self.bind_all('<KeyPress-Down>', lambda evt: self.yview_scroll(1, 'units'))
        self.bind_all('<KeyPress-Up>', lambda evt: self.yview_scroll(-1, 'units'))
        self.bind_all('<MouseWheel>', lambda evt: self.yview_scroll(evt.delta//-120, 'units'))

    def _mouse_out(self, evt):
        print('MOUSE OUT')
        self.unbind_all('<Button-4>')
        self.unbind_all('<Button-5>')
        self.unbind_all('<KeyPress-Down>')
        self.unbind_all('<KeyPress-Up>')
        self.unbind_all('<MouseWheel>')

# if __name__=='__main__':
#     root=tkinter.Tk()
#     scf=ScrollableFrame(root, scrollbar_side='right')
#     scf.pack(expand=True,fill='both')
#     import pkgutil
#     image = tkinter.PhotoImage(master=root, data=pkgutil.get_data('swordfish_launcher.gui', 'sunflower.gif'))
#     for _ in range(20):
#         tkinter.Label(scf.scrollable_region, image=image).pack()
#     root.mainloop()
#




