from .util import BaseDialog


class Secret(BaseDialog):
    def __init__(self, master, config):
        super().__init__(master, config)
        self.add_checkbutton('Super Secret Setting', default=False).pack()
        self.add_checkbutton('Super Secret Setting 4', default=False).pack()
