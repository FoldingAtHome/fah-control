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

import gtk
import re

class EntryValidator:
    def __init__(self, app, entry, pattern, description = ''):
        self.app = app
        self.entry = entry
        self.re = re.compile(pattern)
        self.description = description
        self.text = entry.get_text()

        entry.connect('focus-in-event', self.on_focus_in_event)
        entry.connect('focus-out-event', self.on_focus_out_event)


    def is_valid(self):
        return self.re.match(self.entry.get_text()) is not None


    def on_focus_in_event(self, widget, event, data = None):
        self.text = self.entry.get_text()
        return False # let the signal propagate


    def on_focus_out_event(self, widget, event, data = None):
        if not self.is_valid():
            self.app.error('Invalid value\n%s' % self.description)
            self.entry.set_text(self.text)

        else: self.text = self.entry.get_text()

        return False # let the signal propagate
