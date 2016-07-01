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
import gobject
import copy

from fah.util import parse_bool
from fah.util import status_to_color


class SlotConfig:
    def __init__(
        self, id = -1, status = None, description = None, reason = None,
        idle = False, options = {}, **kw):

        self.id = int(id)
        self.status = status
        self.description = description
        self.reason = reason
        self.idle = idle
        self.options = options

        if status is not None: self.status = status.title()
        if description is None: self.description = 'cpu'

        # Type
        if self.description.startswith('cpu'): self.type = 'cpu'
        elif self.description.startswith('gpu'): self.type = 'gpu'
        else: raise Exception, 'Invalid slot type "%s"' % description


    def add_to_ui(self, app):
        wrapper = gobject.GObject()
        wrapper.slot = copy.deepcopy(self)
        app.slot_list.append((self.id, self.type, wrapper))


    @staticmethod
    def clear_dialog(app):
        app.slot_option_list.clear()
        app.slot_type_cpu.set_active(True)
        for name in 'gpu opencl cuda'.split():
            app.slot_option_widgets[name + '_index'].set_value(-1)
        app.slot_option_widgets['cpus'].set_value(-1)


    def save_dialog(self, app):
        self.options = {}

        if app.slot_type_cpu.get_active():
            self.type = 'cpu'

            cpus = str(int(app.slot_option_widgets['cpus'].get_value()))
            if int(cpus): self.options['cpus'] = cpus

        elif app.slot_type_gpu.get_active():
            self.type = 'gpu'

            for name in 'gpu opencl cuda'.split():
                idx = int(app.slot_option_widgets[name + '_index'].get_value())
                if idx == -1:
                    if name + '-index' in self.options:
                        del self.options[name + '-index']
                else: self.options[name + '-index'] = str(idx)

        # Extra options
        def add_option(model, path, iter, data = None):
            name = model.get(iter, 0)[0]
            value = model.get(iter, 1)[0]
            self.options[name] = value

        app.slot_option_list.foreach(add_option)


    def load_dialog(self, app):
        used = set()

        # Type
        if self.type == 'cpu': app.slot_type_cpu.set_active(True)
        elif self.type == 'gpu': app.slot_type_gpu.set_active(True)
        else: raise Exception, 'Invalid slot type "%s"' % self.type
        used.add('gpu')

        # SMP
        if 'cpus' in self.options: cpus = float(self.options['cpus'])
        else: cpus = -1
        app.slot_option_widgets['cpus'].set_value(cpus)
        used.add('cpus')

        # GPU
        for name in 'gpu opencl cuda'.split():
            if name + '-index' in self.options:
                idx = float(self.options[name + '-index'])
            else: idx = -1
            app.slot_option_widgets[name + '_index'].set_value(idx)
            used.add(name + '-index')

        # Options
        app.slot_option_list.clear()
        for name, value in self.options.items():
            if not name in used:
                app.slot_option_list.append((name, value))
