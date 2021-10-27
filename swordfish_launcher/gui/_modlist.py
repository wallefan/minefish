import tkinter

from swordfish_launcher.downloader.modpack import AbstractModpack
from swordfish_launcher.gui.scrollable_frame import ScrollableFrame


OPTIONHEIGHT = 110
IMAGEWIDTH = 120
OPTIONWIDTH = 200

class ModList(ScrollableFrame):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.packs = []

    def add_pack(self, modpack: AbstractModpack):
        modpack_frame = tkinter.Frame(self.scrollable_region,
                                      background='white' if len(self.packs) % 2 == 0 else 'grey')
        modpack_frame.modpack = modpack
        image = modpack._getimage('icon')
        if image:
            max_dimensions = (image.width * OPTIONHEIGHT // image.height, OPTIONHEIGHT)
            if max_dimensions[0] < IMAGEWIDTH:
                image = image.resize(max_dimensions)
            else:
                image = image.resize((IMAGEWIDTH, image.height * IMAGEWIDTH // image.width))
            from PIL import ImageTk
            photoimage = ImageTk.PhotoImage(image, master=modpack_frame)
            modpack_frame.icon = photoimage
            tkinter.Label(modpack_frame, image=photoimage).pack(side='left', fill='y')#.grid(row=0, column=0, rowspan=3, sticky='w')
        tkinter.Label(modpack_frame, text=modpack.title, font=('', 12, 'bold')).pack(side='top')#.grid(column=1, row=0, sticky='w')
        if modpack.description:
            tkinter.Message(modpack_frame, text=modpack.description, font=('', 6), width=OPTIONWIDTH).pack(side='top')#.grid(column=1, row=1, sticky='w')

        button_frame_1 = tkinter.Frame(modpack_frame)
        button_frame_1.pack(side='top')
        tkinter.ttk.Button(button_frame_1, text='button 1').pack(side='left')
        tkinter.ttk.Button(button_frame_1, text='button 2').pack(side='left')
        tkinter.ttk.Button(button_frame_1, text='button 3').pack(side='left')
        button_frame_2 = tkinter.Frame(modpack_frame)
        button_frame_2.pack(side='top')
        tkinter.ttk.Button(button_frame_2, text='button 4').pack(side='left')
        tkinter.ttk.Button(button_frame_2, text='button 5').pack(side='left')

        self.packs.append(modpack_frame)
        modpack_frame.pack(fill='x', expand=True)

if __name__ == '__main__':
    root = tkinter.Tk()
    modlist = ModList(root)
    modlist.pack(expand=True, fill='both')
    from swordfish_launcher.downloader.third_party.technic import TechnicModpack
    from swordfish_launcher.downloader.third_party.curse import CurseModpack
    from swordfish_launcher.downloader.third_party.atlauncher import ATLPack
    def _worker():
        # with open('ftb_packs.pkl','rb') as f:
        #     import pickle
        #     packs = pickle.load(f)
        # for pack in packs:
        #     print('loading', pack.title)
        #     modlist.add_pack(pack)
        for pack in TechnicModpack.search('Tekkit'):
            modlist.add_pack(pack)
        for pack in CurseModpack.search('FTB'):
            modlist.add_pack(pack)
        for pack in ATLPack.search('SevTech'):
            modlist.add_pack(pack)
        print('done loading')

    import threading
    threading.Thread(target=_worker, daemon=True).start()
    root.mainloop()
