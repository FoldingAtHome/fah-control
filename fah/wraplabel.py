################################################################################
#                                                                              #
#                    Folding@Home Client Control (FAHControl)                  #
#                   Copyright (C) 2016-2020 foldingathome.org                  #
#                  Copyright (C) 2010-2016 Stanford University                 #
#                                                                              #
#      This program is free software: you can redistribute it and/or modify    #
#      it under the terms of the GNU General Public License as published by    #
#       the Free Software Foundation, either version 3 of the License, or      #
#                      (at your option) any later version.                     #
#                                                                              #
#        This program is distributed in the hope that it will be useful,       #
#         but WITHOUT ANY WARRANTY; without even the implied warranty of       #
#         MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the        #
#                  GNU General Public License for more details.                #
#                                                                              #
#       You should have received a copy of the GNU General Public License      #
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.    #
#                                                                              #
################################################################################

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
