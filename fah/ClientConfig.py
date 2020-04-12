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

import sys
from gi.repository import Gtk
import traceback
import re

from fah.util import parse_bool
from fah.util import status_to_color
from fah.util import get_span_markup
from fah.util import get_widget_str_value
from fah.util import set_widget_str_value
from fah import SlotConfig


def get_option_mods(old_options, new_options):
    changes = {}

    # Deleted
    for name in old_options:
        if name not in new_options:
            changes[name + '!'] = None

    # Added and modified
    for name, value in list(new_options.items()):
        if name not in old_options or value != old_options[name]:
            changes[name] = value

    return changes

def get_buffer_text(buffer):
    return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter())


def get_model_column(model, iter, column):
    if iter is not None: return model.get_value(iter, column)


def get_selected_tree_column(tree, column):
    selection = tree.get_selection()
    model = tree.get_model()
    if selection is not None:
        return get_model_column(model, selection.get_selected()[1], column)


def get_active_combo_column(combo, column):
    return get_model_column(combo.get_model(), combo.get_active_iter(), column)


class ClientConfig:
    queue_cols = ('id state statecolor percentdone percent').split()

    def __init__(self):
        self.last_updated = 0
        self.queue = []
        self.queue_map = {}
        self.slots = []
        self.options = {}
        self.core_options = {}
        self.info = []
        self.log = []
        self.log_append_count = 0
        self.tooltip = ''
        self.last_log_filter = ''
        self.log_filter_re = None
        self.updating = False


    def get(self, name):
        if name in self.options: return self.options[name]
    def set(self, name, value): self.options[name] = value
    def have(self, name):
        return name in self.options and self.options[name] is not None


    def get_prcg(self, row):
        return '%s (%s, %s, %s)' % (
            row['project'], row['run'], row['clone'], row['gen'])


    def update_power(self, app):
        power = self.get('power').lower()
        for i in range(len(app.folding_power_levels)):
            if power == app.folding_power_levels[i].lower():
                app.folding_power.set_value(i)


    def update_ppd(self, app, ppd):
        if ppd: s = '%d' % int(ppd)
        else: s = 'Unknown'
        app.client_ppd.set_text(s)


    def update_queue(self, queue):
        self.queue = queue
        self.queue_map = {}
        for values in self.queue:
            self.queue_map[values['id']] = values


    def update_user_info(self, app):
        # User
        user = self.options['user']
        app.donor_info.set_label(user)

        # Team
        team = self.options['team']
        app.team_info.set_label(team)

    def reset_user_info(self, app):
        app.donor_info.set_label('')
        app.team_info.set_label('')


    def get_selected_queue_entry(self, app):
        return get_selected_tree_column(app.queue_tree, 1)


    def get_selected_slot(self, app):
        id = get_selected_tree_column(app.slot_status_tree, 0)
        if id is not None:
            id = int(id)
            for slot in self.slots:
                if slot.id == id: return slot

    def update_queue_ui(self, app):
        if not self.queue:
            app.queue_list.clear()
            return

        # Save selections
        selected = self.get_selected_queue_entry(app)
        selected_row = None
        log_filter_selected = get_active_combo_column(app.log_unit, 1)
        log_filter_row = None

        # Clear queue wo/ updating log filter
        self.updating = True
        try:
            app.queue_list.clear()
        finally:
            self.updating = False

        # Reload queue list
        for values in sorted(self.queue):
            unit_id = values['unit']
            queue_id = values['id']
            status = values['state'].title()
            color = status_to_color(status)
            status = get_span_markup(status, color)
            progress = values['percentdone']
            percent = float(progress[:-1])
            eta = values['eta']
            if eta == '0.00 secs': eta = 'Unknown'
            credit = values['creditestimate']
            if float(credit) == 0: credit = 'Unknown'

            prcg = self.get_prcg(values)
            iter = app.queue_list.append([unit_id, queue_id, status, color,
                                          progress, percent, eta, credit, prcg])

            if queue_id == selected: selected_row = iter
            if queue_id == log_filter_selected: log_filter_row = iter

        # Select the first item if nothing is selected
        if selected_row is None: selected_row = app.queue_list.get_iter_first()
        if log_filter_row is None:
            log_filter_row = app.queue_list.get_iter_first()

        # Restore selections
        app.queue_tree.get_selection().select_iter(selected_row)
        app.log_unit.set_active_iter(log_filter_row)


    def update_work_unit_info(self, app):
        if not self.queue:
            self.reset_work_unit_info(app)
            return

        # Get selected queue entry
        selected = self.get_selected_queue_entry(app)
        if selected is None: return
        entry = self.queue_map[selected]

        # Load info
        for name, value in list(entry.items()):
            if name in app.queue_widgets:
                if (name in ['basecredit', 'creditestimate', 'ppd'] and \
                        float(value) == 0) or value == '<invalid>' or \
                        value == '0.00 secs': value = 'Unknown'

                widget = app.queue_widgets[name]
                set_widget_str_value(widget, value)

        # Status
        status = entry['state'].title()
        color = status_to_color(status)
        status = get_span_markup(status, color)
        widget = app.queue_widgets['state']
        widget.set_markup(status)

        # Links
        base = 'https://apps.foldingathome.org'
        uri = base + '/project.py?p=%s' % entry['project']
        app.queue_widgets['project'].set_uri(uri)

        # PRCG
        prcg = '%s (%s, %s, %s)' % (
            entry['project'], entry['run'], entry['clone'], entry['gen'])
        set_widget_str_value(app.queue_widgets['prcg'], prcg)


    def select_slot(self, app):
        # Get selected slot
        slot = self.get_selected_slot(app)
        if slot is None: return

        # Get associated queue ID
        first_id = None
        first_running_id = None
        for entry in self.queue:
            if int(entry['slot']) == slot.id:
                if first_id is None: first_id = entry['unit']
                if entry['state'].upper() in ['RUNNING', 'FINISHING'] and \
                        first_running_id is None:
                    first_running_id = entry['unit']

        if first_running_id is not None: unit_id = first_running_id
        else: unit_id = first_id

        if unit_id is not None:
            # Find unit_id in the queue list entry and select row
            list = app.queue_list
            iter = list.get_iter_first()
            while iter is not None:
                if list.get_value(iter, 0) == unit_id:
                    app.queue_tree.get_selection().select_iter(iter)
                    break
                iter = list.iter_next(iter)

            # Update the UI
            self.update_work_unit_info(app)
        else: app.queue_tree.get_selection().unselect_all()


    def select_queue_slot(self, app):
        # Get unit ID of selected queue entry
        selected = self.get_selected_queue_entry(app)
        if selected is None: return

         # Get associated slot ID
        entry = self.queue_map[selected]
        slot = int(entry['slot'])

        # Find and select the slot
        list = app.slot_status_list
        iter = list.get_iter_first()
        while iter is not None:
            if int(list.get_value(iter, 0)) == slot:
                app.slot_status_tree.get_selection().select_iter(iter)
                break
            iter = list.iter_next(iter)

        # Update the UI
        self.update_work_unit_info(app)


    def reset_work_unit_info(self, app):
        for widget in list(app.queue_widgets.values()):
            set_widget_str_value(widget, None)


    def update_info(self, app):
        port = app.info

        # Clear
        for child in port.get_children(): port.remove(child)

        # Alignment
        align = Gtk.Alignment.new(0, 0, 1, 1)
        align.set_padding(4, 4, 4, 4)
        port.add(align)

        # Vertical box
        vbox = Gtk.VBox()
        align.add(vbox)

        for category in self.info:
            name = category[0]
            category = category[1:]

            # Frame
            #frame = Gtk.Frame('<b>%s</b>' % name)
            frame = Gtk.Frame()
            frame.name = name
            frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
            # TODO: FIX ME
            #frame.get_label_widget().set_use_markup(True)
            vbox.pack_start(frame,False,True,0)

            # Alignment
            align = Gtk.Alignment.new(0, 0, 1, 1)
            align.set_padding(0, 0, 12, 0)
            frame.add(align)

            # Table
            table = Gtk.Table(len(category), 2)
            table.set_col_spacing(0, 5)
            align.add(table)

            row = 0
            for name, value in category:
                if not value: continue

                # Name
                label = Gtk.Label(label='<b>%s</b>' % name)
                label.set_use_markup(True)
                label.set_alignment(1, 0.5)
                table.attach(label, 0, 1, row, row + 1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)

                # Value
                if value.startswith('http://'):
                    label = Gtk.LinkButton(value, value)
                    label.set_relief(Gtk.ReliefStyle.NONE)
                    label.set_property('can-focus', False)

                else: label = Gtk.Label(label=value)

                label.set_alignment(0, 0.5)
                label.modify_font(app.mono_font)
                table.attach(label, 1, 2, row, row + 1, yoptions = Gtk.AttachOptions.FILL)

                row += 1

        port.realize()
        port.show_all()


    def update_options(self, app):
        used = set()

        for name, widget in list(app.client_option_widgets.items()):
            name = name.replace('_', '-')
            used.add(name)

            try:
                set_widget_str_value(widget, self.options[name])

            except Exception as e: # Don't let one bad widget kill everything
                print(('WARNING: failed to set widget "%s": %s' % (name, e)))

        # Setup passkey and password entries
        app.passkey_validator.set_good()
        app.password_validator.set_good()
        app.proxy_pass_validator.set_good()

        # Set folding power
        if 'power' in self.options:
            used.add('power')
            self.update_power(app)

        # Set proxy options
        if 'proxy-enable' in self.options:
            proxy_enable = parse_bool(self.get('proxy-enable'))
            app.proxy_frame.set_sensitive(proxy_enable)
            app.proxy_auth_frame.set_sensitive(proxy_enable)

        if self.have('proxy'):
            proxy = self.get('proxy')
            if ':' in proxy: proxy_addr, proxy_port = proxy.split(':', 1)
            else: proxy_addr, proxy_port = proxy, '8080'
            set_widget_str_value(app.client_option_widgets['proxy'], proxy_addr)
            set_widget_str_value(app.proxy_port, proxy_port)

        # Set core priority radio button
        core_idle = not self.have('core-priority') or \
            self.get('core-priority') == 'idle'
        app.client_option_widgets['core_priority'].set_active(core_idle)
        app.core_priority_low.set_active(not core_idle)

        # Extra core options
        app.core_option_list.clear()
        if self.have('extra-core-args'):
            used.add('extra-core-args')

            args = self.get('extra-core-args').split()
            for arg in args: app.core_option_list.append([arg])

        # Remaining options
        app.option_list.clear()
        for name, value in list(self.options.items()):
            if name not in used:
                app.option_list.append([name, value])


    def update_status_slots(self, app):
        # Save selection
        selected = get_selected_tree_column(app.slot_status_tree, 0)
        if selected is not None: selected = selected
        selected_row = None
        log_filter_selected = get_active_combo_column(app.log_slot, 0)
        log_filter_row = None

        # Clear list wo/ updating log filter
        self.updating = True
        try:
            app.slot_status_list.clear()
        finally:
            self.updating = False

        # Reload list
        for slot in self.slots:
            id = '%02d' % slot.id
            status = slot.status.title()
            color = status_to_color(status)
            if status == 'Paused' and slot.reason:
                status += ':' + slot.reason
            status = get_span_markup(status, color)
            description = slot.description.replace('"', '')
            iter = app.slot_status_list.append((id, status, color, description))

            if id == selected: selected_row = iter
            if id == log_filter_selected: log_filter_row = iter

        # Selected the first item if nothing is selected
        if selected_row is None:
            selected_row = app.slot_status_list.get_iter_first()
            if selected_row is not None:
                app.slot_status_tree.get_selection().select_iter(selected_row)
                self.select_slot(app)
        if log_filter_row is None:
            log_filter_row = app.slot_status_list.get_iter_first()

        # Restore selections
        if selected_row is not None:
            app.slot_status_tree.get_selection().select_iter(selected_row)
        if log_filter_row is not None:
            app.log_slot.set_active_iter(log_filter_row)


    def update_slots_ui(self, app):
        app.slot_list.clear()
        for slot in self.slots:
            slot.add_to_ui(app)


    def scroll_log_to_end(self, app):
        if not app.log_follow.get_active(): return
        mark = app.log.get_mark('end')
        app.log.move_mark(mark, app.log.get_end_iter())
        app.log_view.scroll_mark_onscreen(mark)


    def log_clear(self, app):
        app.log.set_text('')
        self.log = []


    def log_filter_str(self, app):
        f = []

        # Severity
        if app.log_severity.get_active():
            f.append(r'((WARNING)|(W )|(ERROR)|(E ))')

        # Unit
        if app.log_unit_enable.get_active():
            id = get_active_combo_column(app.log_unit, 1)
            f.append(r'WU%s' % id)

        # Slot
        if app.log_slot_enable.get_active():
            id = get_active_combo_column(app.log_slot, 0)
            f.append(r'FS%s' % id)

        if len(f):
            f = ['.*(^|:)%s' % x for x in f]
            return '(^\*)|(%s):' % ''.join(f)

        return None


    def log_filter(self, line):
        return self.log_filter_re is None or \
            self.log_filter_re.match(line) is not None


    def log_add_lines(self, app, lines):
        filtered = list(filter(self.log_filter, lines))

        if len(filtered):
            text = '\n'.join(filtered)
            #text = text.decode('utf-8', 'ignore')
            app.log.insert(app.log.get_end_iter(), text + '\n')
            self.scroll_log_to_end(app)


    def log_add(self, app, text):
        # TODO deal with split lines
        lines = []
        for line in text.split('\n'):
            if not line: continue
            lines.append(line)
            self.log.append(line)

        self.log_add_lines(app, lines)


    def update_log(self, app):
        if self.updating: return # Don't refilter during updates

        # Check if filter has changed
        log_filter = self.log_filter_str(app)
        if log_filter == self.last_log_filter: return

        # Update filter
        self.last_log_filter = log_filter
        if log_filter is not None: self.log_filter_re = re.compile(log_filter)
        else: self.log_filter_re = None

        # Reload log
        app.log.set_text('')
        self.log_add_lines(app, self.log)


    def update_status_ui(self, app):
        self.update_queue_ui(app)
        self.update_status_slots(app)
        self.update_work_unit_info(app)
        app.update_client_status() # TODO this should probably be moved here


    def reset_status_ui(self, app):
        self.reset_work_unit_info(app)
        app.queue_list.clear()
        app.slot_status_list.clear()
        app.log.set_text('')


    def get_running(self):
        for unit in self.queue:
            if unit['state'].upper() == 'RUNNING': return True
        return False


    def get_option_changes(self, app):
        used = set()
        options = {}

        used.add('power') # Don't set power here

        # Proxy options
        used.add('proxy')
        proxy_addr = get_widget_str_value(app.client_option_widgets['proxy'])
        proxy_port = get_widget_str_value(app.proxy_port)
        proxy = '%s:%s' % (proxy_addr, proxy_port)
        if self.get('proxy') != proxy: options['proxy'] = proxy

        # Core priority radio button
        used.add('core-priority')
        if app.client_option_widgets['core_priority'].get_active():
            if self.have('core-priority') and \
                    self.get('core-priority') != 'idle':
                options['core-priority'] = 'idle'
        elif self.get('core-priority') != 'low':
            options['core-priority'] = 'low'

        # Extra core options
        used.add('extra-core-args')
        if self.have('extra-core-args'):
            old_args = self.get('extra-core-args').split()
        else: old_args = []

        new_args = []
        def add_arg(model, path, iter, data):
            new_args.append(model.get(iter, 0)[0])
        app.core_option_list.foreach(add_arg, None)

        if old_args != new_args:
            if new_args: options['extra-core-args'] = ' '.join(new_args)
            else: options['extra-core-args!'] = None

        # Extra options
        def check_option(model, path, iter, data):
            name, value = model.get(iter, 0, 1)
            used.add(name)
            if self.get(name) != value: options[name] = value

        app.option_list.foreach(check_option, None)

        # Main options
        for name, widget in list(app.client_option_widgets.items()):
            name = name.replace('_', '-')
            if name in used: continue
            value = self.get(name)
            used.add(name)

            try:
                value = get_widget_str_value(widget)
                old_value = self.get(name)
                if value == '' and old_value is None: value = None
                if value != old_value:
                    if value is None: options[name + '!'] = None
                    else: options[name] = value

            except Exception as e: # Don't let one bad widget kill everything
                print(('WARNING: failed to save widget "%s": %s' % (name, e)))

        # Removed options
        for name in self.options:
            if not name in used:
                options[name + '!'] = None

        return options


    def get_slot_changes(self, app):
        # Get new slots
        new_slots = []
        def add_slot(model, path, iter, data = None):
            new_slots.append(model.get(iter, 2)[0].slot)
        app.slot_list.foreach(add_slot)

        # Get old slot IDs
        old_slot_map = {}
        for slot in self.slots: old_slot_map[slot.id] = slot

        # Get new slot IDs
        new_slot_ids = set()
        for slot in new_slots: new_slot_ids.add(slot.id)

        # Find deleted slot IDs
        deleted = []
        for id in old_slot_map:
            if id not in new_slot_ids: deleted.append(id)

        # Find added and modified slots
        added = []
        modified = []
        for slot in new_slots:
            # Added
            if slot.id == -1: added.append((slot.type, slot.options))
            else:
                old_slot = old_slot_map[slot.id]
                options = get_option_mods(old_slot.options, slot.options)
                if options or old_slot.type != slot.type:
                    modified.append((slot.id, slot.type, options))

        return (deleted, added, modified)


    def get_changes(self, app):
        return self.get_option_changes(app), self.get_slot_changes(app)


    def has_changes(self, app):
        options, slots = self.get_changes(app)
        return options or slots != ([], [], [])
