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

import traceback
import time
import re
import copy
import collections
import gtk
import subprocess
import time
import sys
import signal
import os
import shlex

from fah import *
from fah.util import status_to_color, make_row, get_home_dir

debug = False


class Client:
    def __init__(self, app, name, address, port, password):
        self.name = name
        self.address = address
        self.port = port
        self.password = password

        self.set_updated(False)
        self.selected = False
        self.ppd = 0
        self.power = ''

        self.error_messages = set()

        if not name: self.name = self.get_address()

        # Option names
        names = app.client_option_widgets.keys()
        self.option_names = map(lambda name: name.replace('_', '-'), names)
        self.option_names.append('power') # Folding power

        # Init commands
        self.inactive_cmds = [
            'updates clear',
            'updates add 0 4 $heartbeat',
            'updates add 1 5 $ppd',
            ]

        self.active_cmds = self.inactive_cmds + [
            'updates add 2 1 $(options %s *)' % ' '.join(self.option_names),
            'updates add 3 4 $queue-info',
            'updates add 4 1 $slot-info',
            'info',
            'log-updates start',
            'configured',
            ]

        # Objects
        self.config = ClientConfig()
        self.conn = Connection(self.address, self.port, self.password)
        self.conn.set_init_commands(self.inactive_cmds)


    # Class special functions
    def __str__(self): return self.name
    def __cmp__(self, other): return str.__cmp__(self.name, other.name)
    def __hash__(self): return self.name.__hash__()


    # Getters
    @staticmethod
    def make_address(address, port): return '%s:%d' % (address, port)
    def get_address(self): return Client.make_address(self.address, self.port)
    def get_password(self): return self.conn.password


    def get_status(self):
        status = self.conn.get_status()
        if status == 'Online' and not self.is_updated() and self.selected:
            return 'Updating'
        return status


    def get_selected_slot(self, app): return self.config.get_selected_slot(app)


    # Setters
    def set_address(self, address, port):
        self.conn.address = self.address = address
        self.conn.port = self.port = port

    def set_password(self, password):
        self.conn.password = self.password = password


    # State functions
    def is_local(self):
        return self.address == '127.0.0.1' and self.name == 'local'
    def is_online(self): return self.conn.get_status() == 'Online'

    def set_selected(self, selected):
        if self.selected != selected:
            if selected:
                self.set_updated(False)
                self.conn.set_init_commands(self.active_cmds)
            else: self.conn.set_init_commands(self.inactive_cmds)

            self.selected = selected


    def set_updated(self, updated):
        self.options_updated = updated
        self.info_updated = updated
        self.slots_updated = updated
        self.units_updated = updated


    def is_updated(self):
        return self.options_updated and self.info_updated and \
            self.slots_updated and self.units_updated


    # Log functions
    def refresh_log(self):
        self.conn.queue_command('log-updates restart')


    # GUI functions
    def load_dialog(self, app):
        app.client_entries['name'].set_text(self.name)
        app.client_entries['name'].set_sensitive(self.name != 'local')
        app.client_entries['address'].set_text(self.address)
        app.client_entries['address'].set_sensitive(self.name != 'local')
        app.client_entries['port'].set_value(self.port)
        app.client_entries['password'].set_text(self.password)
        if self.is_updated():
            self.config.update_options(app)
            self.config.update_slots_ui(app)

    def get_row(self, app):
        status = self.get_status()
        keys = {'name': self.name, 'status': status,
                'status_color': status_to_color(status),
                'address': self.get_address()}
        return list(make_row(app.client_cols, keys))


    def update_status_ui(self, app):
        self.config.update_status_ui(app)


    def reset_status_ui(self, app):
        self.config.reset_status_ui(app)


    # Slot control
    def unpause(self, slot = ''):
        self.conn.queue_command('unpause %s' % str(slot))


    def pause(self, slot = ''):
        self.conn.queue_command('pause %s' % str(slot))


    def finish(self, slot = ''):
        self.conn.queue_command('finish %s' % str(slot))


    def on_idle(self, slot = ''):
        self.conn.queue_command('on_idle %s' % str(slot))


    def always_on(self, slot = ''):
        self.conn.queue_command('always_on %s' % str(slot))


    # Save functions
    def save(self, db):
        db.insert('clients', name = self.name, address = self.address,
                  port = self.port, password = self.password)


    def save_options(self, options):
        if not options: return

        cmd = 'options'

        for name, value in options.items():
            cmd += ' ' + name
            if name[-1] != '!':
                cmd += "='%s'" % value.encode('string_escape')

        cmd += ' %s *' % ' '.join(self.option_names)

        self.conn.queue_command(cmd)
        self.options_updated = False # Reload


    def save_slots(self, slots):
        if not slots or slots == ([], [], []): return

        deleted, added, modified = slots

        # Deleted
        for id in deleted:
            self.conn.queue_command('slot-delete %d' % id)

        # Modified
        for id, type, options in modified:
            cmd = 'slot-modify %d %s' % (id, type)
            for name, value in options.items():
                if name[-1] == '!': cmd += ' ' + name
                else: cmd += ' %s="%s"' % (name, value)
            self.conn.queue_command(cmd)

        # Added
        for type, options in added:
            cmd = 'slot-add %s' % type
            for name, value in options.items():
                cmd += ' %s="%s"' % (name, value)
            self.conn.queue_command(cmd)

        self.slots_updated = False # Reload


    def save_config(self, options, slots):
        if not options and slots == ([], [], []): return

        self.save_options(options)
        self.save_slots(slots)

        self.conn.queue_command('save')
        self.conn.queue_command('updates reset')


    def set_power(self, power):
        power = power.lower().replace(' ', '_')
        if power != self.power:
            self.power = power
            self.conn.queue_command('option power ' + power)


    # Message processing
    def process_options(self, app, data):
        self.options_updated = True
        self.config.options = data
        if self.selected:
            self.config.update_options(app)
            self.config.update_user_info(app)
            self.config.update_ppd(app, self.ppd)


    def process_info(self, app, data):
        self.info_updated = True
        self.config.info = data
        if self.selected: self.config.update_info(app)


    def process_slots(self, app, data):
        self.slots_updated = True
        slots = []
        for slot in data: slots.append(SlotConfig(**slot))
        self.config.slots = slots
        if self.selected: self.config.update_status_ui(app)


    def process_units(self, app, data):
        self.units_updated = True
        self.config.update_queue(data)
        if self.selected: self.config.update_status_ui(app)


    def process_log_update(self, app, data):
        # Remove color codes
        data = re.sub(r'\033\[\d\d?m', '', data)

        self.config.log_add(app, data)


    def process_log_restart(self, app, data):
        self.config.log_clear(app)
        self.process_log_update(app, data)


    def process_ppd(self, app, ppd):
        self.ppd = ppd
        if self.selected: self.config.update_ppd(app, ppd)


    def process_error(self, app, data):
        msg = 'On client "%s" %s:%d: %s' % (
            self.name, self.address, self.port, data)

        # Only popup dialog once for each error
        if not msg in self.error_messages:
            self.error_messages.add(msg)
            app.error(msg)

        else:
            print ('ERROR: %s' % msg)

        app.set_status(msg)

    def process_configured(self, app, configured):
        if configured: return
        app.configure_dialog.show()


    def process_message(self, app, type, data):
        if debug:
            print ('message: %s %s' % (type, data))

        if type == 'heartbeat': return
        if type == 'ppd': self.process_ppd(app, data)

        if not self.selected: return

        if type == 'options': self.process_options(app, data)
        elif type == 'info': self.process_info(app, data)
        elif type == 'slots': self.process_slots(app, data)
        elif type == 'units': self.process_units(app, data)
        elif type == 'log-restart': self.process_log_restart(app, data)
        elif type == 'log-update': self.process_log_update(app, data)
        elif type == 'error': self.process_error(app, data)
        elif type == 'configured': self.process_configured(app, data)
        # Ignore other message types


    def update(self, app):
        prevStatus = self.get_status()

        try:
            self.conn.update()

            for version, type, data in self.conn.messages:
                try:
                    self.process_message(app, type, data)
                except Exception as e:
                    traceback.print_exc()

            self.conn.messages = []

        except Exception as e:
            print (e)

        # If client status has changed update UI
        newStatus = self.get_status()
        if prevStatus != newStatus:
            list = app.client_list
            iter = list.get_iter_first()
            while iter is not None:
                name, status = app.client_list.get(iter, 0, 1)

                if name == self.name:
                    # Update client status and colors
                    color = status_to_color(newStatus)
                    path = list.get_path(iter)
                    list.set(iter, 1, newStatus)
                    list.set(iter, 2, color)
                    list.row_changed(path, iter)
                    break

                iter = list.iter_next(iter)

            if not self.is_online(): self.set_updated(False)

            # Update client status label
            if self.selected: app.update_client_status()


    def reconnect(self):
        self.conn.close()


    def close(self):
        # Avoid broken pipe on OSX
        if sys.platform == 'darwin':
            try:
                if self.conn.is_connected():
                    self.conn.queue_command('quit')
                    self.conn.write_some()

            except Exception as e:
                print (e)

        self.conn.close()
