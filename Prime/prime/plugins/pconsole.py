
import gtk

from zope.interface import implements

from twisted.plugin import IPlugin

from prime.iprime import IMenuApplication

from prime.gtk2console import gtk_console

class ConsoleMenuApp:
    implements(IMenuApplication, IPlugin)

    win = None

    def register(self, menuSection):
        mi = gtk.MenuItem(">>> Python Shell")
        mi.connect('activate', self.doit)
        mi.show_all()
        menuSection.append(mi)

    def doit(self, evt):
        if self.win is not None:
            self.win.hide()
            self.win.show_all()
        else:
            self.win = gtk_console({}, self.closewin)

    def closewin(self, *ignored):
        self.win.hide()
        return True

cma = ConsoleMenuApp()
