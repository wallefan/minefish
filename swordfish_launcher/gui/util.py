"""Miscellaneous GUI utilities such as tooltips.
"""

from tkinter import *

# So I've done some research, and it appears the only way to get a balloon/tooltip with Tkinter (at least without tix,
# which is deprecated and doesn't come with Tk, you have to install it separately) is to pop up a Toplevel with a
# Label in it, hide its window controls, and position it onscreen under the cursor.

# This is how IDLE does it, and also what pmw.Balloon is under the hood.

import idlelib.tooltip


def bind_tooltip(widget, text):
    box = None

    def show(evt=None):
        nonlocal box
        if box is not None:
            return
        box = Toplevel(widget)
        x = widget.winfo_rootx() + 25
        y = widget.winfo_rooty() + 20
        if evt:
            x += evt.x - 15
            y += evt.y - 10
        box.overrideredirect(True)
        box.wm_geometry('+{}+{}'.format(x, y))
        Label(box, text=text).pack()

    def hide(evt=None):
        nonlocal box
        box.destroy()
        box = None
    widget.bind('<Enter>', show)
    widget.bind('<Leave>', hide)


if __name__=='__main__':
    tk=Tk()
    button=Button(tk, text='yo')
    button.pack()
    bind_tooltip(button, 'hello there my good sir')
    tk.mainloop()

