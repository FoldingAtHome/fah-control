'''
  Folding@Home Client Control (FAHControl)
  Copyright (C) 2010-2014 Stanford University

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


class WidgetMap(dict):
    def __init__(self, widgets, suffix = None, prefix = None):
        self.suffix = suffix
        self.prefix = prefix
        self.list = []

        try:
            for widget in widgets: self.find(widget)
        except: self.find(widgets)

    def add(self, widget):
        if widget is None: return
        name = gtk.Buildable.get_name(widget)

        if self.suffix is not None: name = name[0:-len(self.suffix)]
        if self.prefix is not None: name = name[len(self.prefix):]
        self[name] = widget
        self.list.append(widget)

    def find(self, widget):
        name = gtk.Buildable.get_name(widget)

        if (name and (self.suffix is None or name.endswith(self.suffix)) and
            (self.prefix is None or name.startswith(self.prefix))):
            self.add(widget)

        if isinstance(widget, gtk.Container):
            widget.foreach(self.find)
