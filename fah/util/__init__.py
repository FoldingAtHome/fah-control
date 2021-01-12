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


# fah.util
from .OrderedDict import *
from .PasswordValidator import *
from .EntryValidator import *
from .SingleApp import *
from .PYONDecoder import *
from gi.repository import Gtk
import sys
import os
import gi
gi.require_version('Gtk', '3.0')


def parse_bool(x):
    if isinstance(x, bool):
        return x
    return x.lower() in ['true', 't', '1', 'yes', 'y']


def status_to_color(status):
    status = status.upper()

    if status == 'PAUSED' or status == 'UPDATING':
        return '#ffff55'
    elif status == 'FINISHED' or status == 'OFFLINE' or status == 'UPLOADED':
        return '#0080c0'
    elif status == 'RUNNING' or status == 'ACTIVE' or status == 'ONLINE':
        return '#1dd923'
    elif status == 'FINISHING':
        return '#7AD980'
    elif status == 'FAILED' or status == 'ERROR' or status == 'FAULTY':
        return '#ff0000'
    elif status == 'SHUTDOWN' or status == 'CONNECTING':
        return '#ff8b00'
    elif status == 'OFFLINE':
        return '#dddddd'
    elif status == 'READY':
        return '#1ef0bc'
    elif status == 'DUMP':
        return '#d2c272'
    else:
        return None


def get_span_markup(text, bg=None, fg='black'):
    markup = '<span'
    if bg is not None:
        markup += ' background="%s"' % bg
    if fg is not None:
        markup += ' foreground="%s"' % fg
    markup += '>%s</span>' % text
    return markup


def iterate_container(widget):
    yield widget

    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            for x in iterate_container(child):
                yield x


def make_row(cols, keys):
    for col in cols:
        if col in keys:
            yield keys[col]
        else:
            yield ''


def get_combo_items(widget):
    items = []

    def iterate_list(model, path, iter, data=None):
        items.append(model.get_value(iter, 0))

    widget.get_model().foreach(iterate_list, None)

    return items


def get_widget_str_value(widget):
    if isinstance(widget, (Gtk.SpinButton, Gtk.Range)):
        # Must come before Gtk.Entry for Gtk.SpinButton

        # Clean up float formatting
        value = '%.2f' % widget.get_value()
        if value.endswith('.00'):
            value = value[0:-3]
        elif value.endswith('.0'):
            value = value[0:-2]
        return value

    elif isinstance(widget, Gtk.Entry):
        return widget.get_text()

    elif isinstance(widget, Gtk.RadioButton):
        # TODO interpret as a number? or name?
        pass

    elif isinstance(widget, Gtk.ToggleButton):
        if widget.get_active():
            return 'true'
        else:
            return 'false'

    elif isinstance(widget, Gtk.ComboBox):
        if widget.get_id_column() != -1:
            return widget.get_active_id()

        # TODO duplication of ClientConfig.get_active_combo_column
        if widget.get_active_iter() is None:
            return None

        return widget.get_model().get_value(widget.get_active_iter(), 0)

    else:
        print('ERROR: unsupported widget type %s' % type(widget))


def set_widget_str_value(widget, value):
    if value is None:
        value = ''
    value = str(value)

    if isinstance(widget, (Gtk.SpinButton, Gtk.Range)):
        # Must come before Gtk.Entry for Gtk.SpinButton
        if value == '':
            value = 0
        else:
            try:
                value = float(value)
            except:
                value = 0
        widget.set_value(value)

    elif isinstance(widget, (Gtk.Entry, Gtk.Label)):
        if widget.get_text() != value:
            widget.set_text(value)
    elif isinstance(widget, Gtk.RadioButton):
        pass  # Ignore for now
    elif isinstance(widget, Gtk.ToggleButton):
        widget.set_active(parse_bool(value))
    elif isinstance(widget, Gtk.Button):
        # NOTE: For some reason setting Button labels causes tooltips to hide.
        # Only set when it has actually changed.
        if widget.get_label() != value:
            widget.set_label(value)

    elif isinstance(widget, Gtk.ComboBox):
        items = get_combo_items(widget)
        length = len(items)
        for i in range(length):
            if items[i].lower() == value.lower():
                widget.set_active(i)
                return
        if length > 0:
            widget.set_active(0)

    elif isinstance(widget, Gtk.ProgressBar):
        widget.set_text(value)

        if value == '':
            value = '0'

        if value.endswith('%'):
            fraction = float(value[:-1]) / 100.0
        else:
            fraction = float(value)

        widget.set_fraction(fraction)

    else:
        print('ERROR: unsupported option widget type %s' % type(widget))


def set_widget_change_action(widget, action):
    if isinstance(widget, (Gtk.Editable, Gtk.ComboBox)):
        widget.connect('changed', action)

    elif isinstance(widget, Gtk.Range):
        widget.connect('value_changed', action)

    elif isinstance(widget, Gtk.ToggleButton):
        widget.connect('toggled', action)

    elif isinstance(widget, Gtk.TreeModel):
        widget.connect('row_changed', action)
        widget.connect('row_inserted', action)
        widget.connect('row_deleted', action)
        widget.connect('rows_reordered', action)

    else:
        print('ERROR: unsupported option widget type %s' % type(widget))


def get_home_dir():
    if sys.platform == 'win32':
        return '.'

    path = os.path.expanduser("~")

    if sys.platform == 'darwin':
        path = os.path.join(path, 'Library/Application Support/FAHClient')

    else:
        path = os.path.join(path, '.FAHClient')

    if not os.path.exists(path):
        os.makedirs(path)

    return path


def get_theme_dirs():
    return [get_home_dir() + '/themes', Gtk.rc_get_theme_dir(),
            '/usr/share/themes']
