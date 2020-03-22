import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango


class WrapLabel(Gtk.Label):
    __gtype_name__ = 'WrapLabel'

    def __init__(self, str = None):
        Gtk.Label.__init__(self)

        self.__wrap_width = 0
        self.layout = self.get_layout()
        self.layout.set_wrap(Pango.WrapMode.WORD_CHAR)

        if str != None: self.set_text(str)

        self.set_alignment(0, 0)


    def do_size_request(self, requisition):
        layout = self.get_layout()
        width, height = layout.get_pixel_size()
        requisition.width = 0
        requisition.height = height


    def do_size_allocate(self, allocation):
        Gtk.Label.do_size_allocate(self, allocation)
        self.__set_wrap_width(allocation.width)


    def set_text(self, str):
        Gtk.Label.set_text(self, str)
        self.__set_wrap_width(self.__wrap_width)


    def set_markup(self, str):
        Gtk.Label.set_markup(self, str)
        self.__set_wrap_width(self.__wrap_width)


    def __set_wrap_width(self, width):
        if width == 0: return
        layout = self.get_layout()
        layout.set_width(width * Pango.SCALE)
        if self.__wrap_width != width:
            self.__wrap_width = width
            self.queue_resize()
