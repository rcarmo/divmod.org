

####### FIRST THING ########
import pygtk
pygtk.require("2.0")
from twisted.internet import gtk2reactor
gtk2reactor.install()

####### UH OKAY DONE #######

import os

from twisted.plugin import getPlugins

from twisted.python.filepath import FilePath
from twisted.python.util import sibpath

from twisted.internet.task import LoopingCall

from twisted.internet import reactor

import gtk.glade
import egg.trayicon

from prime import iprime

import prime.plugins


class IconAnimator:
    lc = None
    def __init__(self, box, icons):
        self.box = box
        self.icons = icons
        for icon in icons:
            icon.show()
        self.stop()

    def tick(self):
        self.position += 1
        self.position %= len(self.icons)
        c = self.box.get_children()
        if c:
            self.box.remove(c[0])
        self.box.add(self.icons[self.position])

    def start(self):
        self.animating = True
        self.tick()
        self.lc = LoopingCall(self.tick)
        self.lc.start(1.0)

    def stop(self, index=0):
        self.animating = False
        self.position = index - 1
        self.tick()
        if self.lc is not None:
            self.lc.stop()
            self.lc = None



class MenuSection:
    """
    I represent a section of a GTK menu.  Items may be added to me.
    """

    def __init__(self, menu):
        self.menu = menu
        self.items = []
        self.dividerItem = gtk.SeparatorMenuItem()
        self.menu.append(self.dividerItem)

    def append(self, menuItem):
        """
        Append an item to this section of the menu.
        """
        myIndex = self.menu.get_children().index(self.dividerItem)
        self.menu.insert(menuItem, myIndex + len(self.items))

    def remove(self, menuItem):
        self.menu.remove(menuItem)


class NotificationEntry:
    def __init__(self):
        icon = egg.trayicon.TrayIcon("Vertex")
        workingdir = FilePath(os.path.expanduser("~/.vertex"))
        eventbox = gtk.EventBox()
        icon.add(eventbox)
        icon.show_all()

        icons = []
        for pth in 'inactive', 'active':
            im = gtk.Image()
            im.set_from_file(sibpath(__file__, 'icon-'+pth+'.png'))
            icons.append(im)

        self.animator = IconAnimator(eventbox, icons)
        self.menu = gtk.Menu()

        plugs = getPlugins(iprime.IMenuApplication, prime.plugins)
        print 'PLUGGIN'
        for plug in plugs:
            # XXX TODO: this little for loop is really the integration hub for
            # all Prime applications, it should be waaaaay more sophisticated.
            # (By that, I mainly mean that applications should be able to
            # easily find each other without resorting to import hackery: if
            # the Faucet wants to send an email through ... what the heck are
            # we going to call the Quotient client, the Divisor???, it should
            # totally be able to.
            print 'PLUG!', plug

            m = MenuSection(self.menu)
            plug.register(m)
        print 'DEPLUGGIN'

        imi = gtk.ImageMenuItem(stock_id=gtk.STOCK_QUIT)
        self.menu.append(imi)
        imi.connect('activate', lambda ev: reactor.stop() and True)
        self.menu.show_all()
        eventbox.connect('button_press_event', self.popupMenu)


    def popupMenu(self, box, event):
        def positionRelative(mmenu):
            # this function was cribbed from Tomboy's Tomboy/Utils.cs
            x, y = box.window.get_origin()
            x += box.allocation.x
            reqw, reqh = mmenu.size_request()
            if y + reqh >= box.get_screen().get_height():
                y -= reqh
            else:
                y += box.allocation.height
            pushIn = True
            return x, y, pushIn
        def deactivateMenu(mmenu):
            self.menu.popdown()
            box.set_state(gtk.STATE_NORMAL)
        self.menu.connect("deactivate", deactivateMenu)
        self.menu.popup(None, None, positionRelative, event.button, event.get_time())
        box.set_state(gtk.STATE_SELECTED)


def main():
    import gnome
    gnome.program_init("Prime", "0.01")
    pix = gtk.gdk.pixbuf_new_from_file(sibpath(__file__, "icon-active.png"))
    gtk.window_set_default_icon_list(pix)
    # global ne
    ne = NotificationEntry()
    from twisted.python import log
    import sys
    sys.stdin.close()
    log.startLogging(sys.stdout)
    reactor.run()
