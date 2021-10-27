import tkinter

OFF_COLOR = "#ffffff"
ON_COLOR = "#000000"

BLOCK_WIDTH = 5
BLOCK_SPACING = 8

def _mkrect(canvas:tkinter.Canvas, xofs,yofs,xpos,ypos):
    return canvas.create_rectangle((xofs+BLOCK_SPACING*xpos, yofs+BLOCK_SPACING*ypos,
                                    xofs+BLOCK_SPACING*xpos+BLOCK_WIDTH, yofs+BLOCK_SPACING*ypos+BLOCK_WIDTH))

class Throbber:
    def __init__(self, canvas:tkinter.Canvas, xofs, yofs):
        self.position = 0
        self.canvas = canvas
        self.segments = [
            _mkrect(canvas, xofs, yofs, 0, 0),
            _mkrect(canvas, xofs, yofs, 1, 0),
            _mkrect(canvas, xofs, yofs, 2, 0),
            _mkrect(canvas, xofs, yofs, 2, 1),
            _mkrect(canvas, xofs, yofs, 2, 2),
            _mkrect(canvas, xofs, yofs, 1, 2),
            _mkrect(canvas, xofs, yofs, 0, 2),
            _mkrect(canvas, xofs, yofs, 0, 1),
        ]
        self.set_active(False)

    def set_active(self, active):
        self.active = active
        if active:
            self.position = 0
            self.advance()

    def advance(self):
        self.canvas.itemconfigure(self.segments[self.position], fill=OFF_COLOR)
        self.position += 1
        self.position %= 8
        self.canvas.itemconfigure(self.segments[self.position], fill=ON_COLOR)
        if self.active:
            self.canvas.after(62,self.advance)

if __name__=='__main__':
    root = tkinter.Tk()
    canvas = tkinter.Canvas(root, width=640,height=480)
    canvas.pack()
    Throbber(canvas, 10, 10).set_active(True)
    root.mainloop()