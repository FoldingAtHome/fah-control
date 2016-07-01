'''
  Folding@Home Client Control (FAHControl)
  Copyright (C) 2010-2016 Stanford University

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import gtk

from fah.util.EntryValidator import EntryValidator


class PasswordValidator(EntryValidator):
    def __init__(self, app, password_entry, reenter_entry, valid_image,
                 valid_text, pattern = r'^.*$', description = ''):
        EntryValidator.__init__(self, app, password_entry, pattern, description)

        self.password_entry = password_entry
        self.reenter_entry = reenter_entry
        self.valid_image = valid_image
        self.valid_text = valid_text

        self.update()

        password_entry.connect('changed', self.on_changed)
        reenter_entry.connect('changed', self.on_changed)


    def set_good(self):
        if not self.is_valid(): self.password_entry.set_text('')
        password = self.password_entry.get_text()
        self.reenter_entry.set_text(password)


    def is_good(self):
        return self.entries_match() and self.is_valid()


    def entries_match(self):
        password = self.password_entry.get_text()
        reenter = self.reenter_entry.get_text()
        return password == reenter


    def update(self):
        valid = False
        if self.is_valid():
            if self.entries_match(): valid = True
            else:
                self.valid_text.set_text('Entries do not match')
        else: self.valid_text.set_text('Entry is invalid')

        if valid:
            self.valid_image.set_from_stock(gtk.STOCK_YES, gtk.ICON_SIZE_BUTTON)
            self.valid_text.set_text('Entries match')
        else:
            self.valid_image.set_from_stock(gtk.STOCK_DIALOG_ERROR,
                                            gtk.ICON_SIZE_BUTTON)


    def on_changed(self, widget, data = None):
        self.update()
        return False # Let the signal propagate
