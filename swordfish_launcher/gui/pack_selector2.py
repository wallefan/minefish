import tkinter.ttk
import tkinter
# from . import SwordfishLauncher
import urllib

try:
    from PIL import Image, ImageTk

    has_pil = True
except ImportError:
    has_pil = False

OPTIONHEIGHT = 200

IMAGEWIDTH = 200


class ScrollableList(tkinter.Canvas):
    def __init__(self, parent, scrollbar_side='left'):
        super().__init__(parent)
        self.scrollbar = tkinter.ttk.Scrollbar(parent, command=self.yview)
        self.scrollbar.pack(side=scrollbar_side, expand=False, fill='y')
        self.bind('<Button-1>', self.onClick)
        self.config(yscrollcommand=self.scrollbar.set)
        self.options = []
        self._images = []

    def onClick(self, evt: tkinter.Event):
        #clicked_elements = self.find_closest(self.canvasx(evt.x), self.canvasy(evt.y))
        print((self.yview()+evt.y)//OPTIONHEIGHT)

    def addOption(self, image, text):
        new_frame = tkinter.Frame(self)
        new_frame.pack()
        self.options.append(new_frame)
        if isinstance(image, tkinter.PhotoImage):
            self.create_window(window=tkinter.Label(new_frame, image=image))
            tkinter.Label(new_frame, text=text).pack(side='left')
        # elif has_pil and image is not None:
        #     if isinstance(image, str):
        #         with urllib.request.urlopen(urllib.request.Request(image,
        #                                                            headers={  # quick question pycharm what the f***
        #                                                                'User-Agent': 'SwordfishLauncher 1.0'})) as req:
        #             image = Image.open(req)
        #             image.load()  # make sure this happens before the connection is closed.
        #     max_dimensions = (image.width * OPTIONHEIGHT // image.height, OPTIONHEIGHT)
        #     if max_dimensions[0] < IMAGEWIDTH:
        #         image = image.resize(max_dimensions)
        #     else:
        #         image = image.resize((IMAGEWIDTH, image.height * IMAGEWIDTH // image.width))
        #     photoimage = ImageTk.PhotoImage(image)
        #     self._images.append(photoimage)
        #     self.create_image(IMAGEWIDTH / 2, pos + OPTIONHEIGHT // 2, image=photoimage)
        #     self.create_text(IMAGEWIDTH, pos, anchor='nw', text=text, font=('', 20))
        # else:
        #     self.create_text(15, pos, anchor='nw', text=text)
        self.configure(scrollregion=self.bbox('all'))


if __name__ == '__main__':
    import pkgutil

    root = tkinter.Tk()
    thing = ScrollableList(root)
    image = tkinter.PhotoImage(master=root, data=pkgutil.get_data('swordfish_launcher.gui', 'sunflower.gif'))
    for i in range(20):
        thing.addOption(image, str(i))
    thing.pack()
    root.mainloop()
