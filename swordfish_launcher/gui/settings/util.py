import tkinter
import configparser

class BaseDialog(tkinter.Frame):
    section_name=None
    def __init__(self, master, config):
        super().__init__(master)
        section = self.section_name or self.__class__.__name__
        if not config.has_section(section):
            config.add_section(section)
        self.config: configparser.SectionProxy = config[section]

    def add_checkbutton(self, text, cfgname=None, *, default, onvalue='yes', offvalue='no'):
        if not cfgname:
            cfgname = text
        var = tkinter.StringVar()
        if isinstance(default, bool):
            default = onvalue if default else offvalue
        var.set(self.config.get(cfgname, default))

        return tkinter.Checkbutton(self, variable=var, text=text, command=self.monitor_variable(var, cfgname, None),
                                   onvalue=onvalue, offvalue=offvalue)

    def monitor_variable(self, var, cfgpath, default):
        if default:
            if cfgpath in self.config:
                var.set(type(default)(self.config[cfgpath]))
            else:
                var.set(default)
        # else it is the caller's responsibility

        def on_changed():
            self.config[cfgpath] = str(var.get())
        return on_changed
