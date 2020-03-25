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
import time
import re
import traceback
import platform
import urllib

import gtk
import glib
import pygtk
pygtk.require("2.0")
import pango
import webbrowser
import shlex
import subprocess
from fah.wraplabel import WrapLabel

# OSX integration
if sys.platform == 'darwin':
    try:
        from gtk_osxapplication import *
    except:
        import gtkosx_application
        from gtkosx_application import Application as OSXApplication
        from gtkosx_application import gtkosx_application_get_resource_path \
            as quartz_application_get_resource_path

from fah import *
from fah.db import *
from fah.util import *


def set_tree_view_font(widget, font):
    for widget in iterate_container(widget):
        if isinstance(widget, gtk.TreeView):
            widget.modify_font(font)


def append_tree_entry(model, path, iter, selection):
    selection.append((path, iter))


def get_tree_selection(tree_view):
    selection = []
    tree_view.get_selection().selected_foreach(append_tree_entry, selection)
    return selection


def remove_tree_selection(tree_view, callback = None):
    for path, iter in get_tree_selection(tree_view):
        if callback is not None: callback(path, iter)
        tree_view.get_model().remove(iter)


def osx_version():
    """ returns osx version as tuple of integers """
    if sys.platform != 'darwin': return None
    try:
        ver = tuple([int(x) for x in platform.mac_ver()[0].split('.')])
    except Exception as e:
        print (e)
        darwin_ver = platform.release().split('.')
        ver = (10, int(darwin_ver[0]) - 4, int(darwin_ver[1]))
    return ver


def osx_add_GtkApplicationDelegate_methods():
    # GtkApplicationDelegate Category via PyObjC
    def applicationShouldHandleReopen_hasVisibleWindows_(self, app, flag):
        # reopen event or dock icon clicked
        # restore windows if hidden
        controller = FAHControl.instance
        if controller is not None: controller.restore()
        return True
    try:
        import objc
        cls = objc.lookUpClass('GtkApplicationDelegate')
        sig1 = '%s%s%s%s%s' % (objc._C_NSBOOL, objc._C_ID, objc._C_SEL,
            objc._C_ID, objc._C_NSBOOL)
        objc.classAddMethods(cls, [
            objc.selector(
                applicationShouldHandleReopen_hasVisibleWindows_,
                signature = sig1)
                ])
    except Exception as e:
        print (e)


def osx_accel_window_close(accel_group, acceleratable, keyval, modifier):
    acceleratable.hide()
    return True


def osx_accel_window_minimize(accel_group, acceleratable, keyval, modifier):
    acceleratable.iconify()
    return True


def load_fahcontrol_db():
    db = Database(os.path.join(get_home_dir(), 'FAHControl.db'))
    db.validate()

    return db


class FAHControl(SingleAppServer):
    client_cols = 'name status status_color address'.split()

    # NOTE: These URLs are here rather than in the Glade file because the
    #  Glade editor strips the '&'s on save.  Even if you use '&amp;' the
    #  ampersands get striped when resaved.
    team_stats_links = [
        ['Folding@home', 'https://stats.foldingathome.org/team/%(team)s'],
        ['Extreme Overclocking', 'http://folding.extremeoverclocking.com/'
         'team_summary.php?t=%(team)s'],
        ['Kakao Stats', 'http://kakaostats.com/tsum.php?t=%(team)s'],
        ['[H]ard Folding', 'http://www.hardfolding.com/fh_stats/index.php'
         '?pz=101&tnum=%(team)s'],
        ['Custom', ''],
        ]
    donor_stats_links = [
        ['Folding@home', 'https://stats.foldingathome.org/donor/%(donor)s'],
        ['Custom', ''],
        ]

    folding_power_levels = ['Light', 'Medium', 'Full']

    instance = None

    def __init__(self, glade = 'FAHControl.glade'):
        SingleAppServer.__init__(self)

        self.__class__.instance = self

        # Vars
        self.clients = {}
        self.clientsByAddress = {}
        self.active_client = None
        self.client_is_online = False
        self.selected_clients = set()
        self.status_clear_time = None
        self.window_visible = False
        self.viewer = None
        self.last_db_flush = 0
        self.last_clients_update = 0
        self.error_dialog = None
        self.restore_dialogs = []
        self.last_clock = None
        self.timer_id = None
        self.folding_power_changing = False

        # Open database
        try:
            self.db = load_fahcontrol_db()

        except Exception as e:
            print (e)
            sys.exit(1)

        # OSX integration
        if sys.platform == 'darwin':
            self.osx_app = OSXApplication()
            self.osx_app.set_use_quartz_accelerators(True)
            self.osx_version = osx_version()
            self.is_old_gtk = gtk.gtk_version < (2,24)
            osx_add_GtkApplicationDelegate_methods()

        # URI hook
        gtk.link_button_set_uri_hook(self.on_uri_hook, None)

        # Style
        settings = gtk.settings_get_default()
        self.system_theme = settings.get_property('gtk-theme-name')
        if sys.platform == 'darwin':
            # Load standard key bindings for Mac and disable mnemonics
            resources = quartz_application_get_resource_path()
            rcfile = os.path.join(resources, 'themes/Mac/gtk-2.0-key/gtkrc')
            if os.path.exists(rcfile): gtk.rc_parse(rcfile)
        rcfile = os.path.join(os.path.expanduser("~"), '.FAHClient/gtkrc')
        if os.path.exists(rcfile): gtk.rc_parse(rcfile)
        self.mono_font = pango.FontDescription('Monospace')
        small_font = pango.FontDescription('Sans 8')

        # Default icon
        gtk.window_set_default_icon(get_icon('small'))

        # Filter glade
        if len(glade) < 1024: glade = open(glade, 'r').read()
        glade = re.subn('class="GtkLabel" id="wlabel',
                        'class="WrapLabel" id="wlabel', glade)[0]
        if sys.platform == 'darwin':
            # glade editor strips accel modifiers. add if missing
            glade = re.subn('accelerator *key="comma" *signal',
                'accelerator key="comma" modifiers="GDK_META_MASK" signal',
                glade)[0]

        # Build GUI
        self.builder = builder = gtk.Builder()
        try:
            builder.add_from_string(glade)
        except:
            self.error('Failed to load UI file: %s' % glade)
            sys.exit(1)

        # Main window
        self.window = builder.get_object('window')
        self.window.set_geometry_hints(None, 440, 256, -1, -1, 800, 512)
        set_tree_view_font(self.window, self.mono_font)
        self.status_bar = builder.get_object('status_bar')
        self.ppd_label = builder.get_object('ppd_label')
        self.time_label = builder.get_object('time_label')

        # Panes
        self.panes = WidgetMap(self.window, 'paned')
        for name, pane in self.panes.items():
            prop = name + '_position'

            # Load current value
            if self.db.has(prop):
                value = int(self.db.get(prop))
                if value and value < 100: value = 100 # mimimum if not hidden
                pane.set_position(value)

            pane.connect('notify::position', self.store_property, prop)

        # Dialogs
        self.preferences_dialog = builder.get_object('preferences_dialog')
        self.client_dialog = builder.get_object('client_dialog')
        self.options_dialog = builder.get_object('options_dialog')
        self.core_options_dialog = builder.get_object('core_options_dialog')
        self.slot_dialog = builder.get_object('slot_dialog')
        self.about_dialog = builder.get_object('about_dialog')
        self.configure_dialog = builder.get_object('configure_dialog')
        # Note: The order of these dialogs is important since they are restored
        #   in this order.  Child dialogs cannot be restored before their
        #   parents so they must be last.  See restore() below.
        self.dialogs = [
            self.about_dialog, self.preferences_dialog, self.client_dialog,
            self.slot_dialog, self.options_dialog, self.core_options_dialog,
            self.configure_dialog]

        # Dialog & window sizes
        self.windows = {
            'preferences': self.preferences_dialog,
            'client': self.client_dialog,
            'options': self.options_dialog,
            'core_options': self.core_options_dialog,
            'slot': self.slot_dialog,
            'about': self.about_dialog,
            'main': self.window,
            }
        for name, win in self.windows.items():
            if self.db.has(name + '_width'):
                width = int(self.db.get(name + '_width'))
            else: width = -1

            if self.db.has(name + '_height'):
                height = int(self.db.get(name + '_height'))
            else: height = -1

            if name == 'main':
                if 0 < width and width < 600: width = 600
                if 0 < height and height < 400: height = 400

            if 100 <= width and 100 <= height: win.resize(width, height)

            win.connect('configure_event', self.store_dimensions, name)

        # Tool bar
        builder.get_object('toolbar1').modify_font(small_font)
        button = builder.get_object('viewer_button')
        button.get_image().set_from_pixbuf(get_viewer_icon('small'))

        # About Dialog
        icon = builder.get_object('about_icon')
        icon.set_from_pixbuf(get_icon('medium'))
        about_version = builder.get_object('about_version')
        about_version.set_markup('<b>Version: %s</b>' % version)

        # Preferences
        self.theme_list = self.load_themes()
        widget = builder.get_object('theme_list')
        for theme in self.theme_list: widget.append(theme)

        # Client list
        self.client_hpane = builder.get_object('client_hpane')
        self.client_notebook = builder.get_object('client_notebook')
        self.client_config_notebook = \
            builder.get_object('client_config_notebook')
        self.client_config_notebook.set_current_page(1)
        self.client_tree = builder.get_object('client_tree_view')
        self.client_list = builder.get_object('client_list')
        self.client_label = builder.get_object('client_label')
        self.client_config_label = builder.get_object('client_config_label')
        self.client_tree.grab_focus()
        selection = self.client_tree.get_selection()
        selection.connect('changed', self.on_client_selection_changed)

        # Option lists
        self.option_tree, self.option_list = self.connect_option_view('')
        self.slot_option_tree, self.slot_option_list =\
            self.connect_option_view('slot_')
        self.core_option_tree = builder.get_object('core_option_tree_view')
        self.core_option_list = builder.get_object('core_option_list')
        self.option_tree.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.slot_option_tree.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.core_option_tree.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        # Option dialog
        self.option_name_entry = builder.get_object('option_name_entry')
        self.option_value_entry = builder.get_object('option_value_entry')

        # Core option dialog
        self.core_option_entry = builder.get_object('core_option_entry')

        # Folding power
        self.folding_power_label = builder.get_object('folding_power_label')
        self.folding_power = builder.get_object('folding_power_hscale')
        for i in range(len(self.folding_power_levels)):
            level = self.folding_power_levels[i]
            markup = '<span font_size="small" weight="bold">%s</span>' % level
            self.folding_power.add_mark(i, gtk.POS_BOTTOM, markup)

        # User info
        self.donor_info = builder.get_object('donor_info')
        self.team_info = builder.get_object('team_info')

        # Client stats
        self.client_ppd = builder.get_object('client_ppd')

        # Client config
        self.core_priority_low = builder.get_object('core_priority_low')

        # Proxy
        self.proxy_frame = builder.get_object('proxy_frame')
        self.proxy_auth_frame = builder.get_object('proxy_auth_frame')
        self.proxy_port = builder.get_object('proxy_port_entry')

        # Project
        self.project_frame = builder.get_object('project_frame')
        self.project_text = builder.get_object('project_text')
        self.project_label = builder.get_object('project_label')

        # Slot lists
        self.slot_status_tree = builder.get_object('slot_status_tree_view')
        self.slot_status_tree.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.slot_status_list = builder.get_object('slot_status_list')
        self.slot_tree = builder.get_object('slot_tree_view')
        self.slot_list = builder.get_object('slot_list')
        self.slot_menu = builder.get_object('slot_menu')
        self.idle_slot_item = builder.get_object('idle_slot_item')
        view_slot_item = builder.get_object('view_slot_item')
        view_slot_item.get_image().set_from_pixbuf(get_viewer_icon('tiny'))

        # Slot dialog
        self.slot_type_cpu = builder.get_object('slot_type_cpu')
        self.slot_type_gpu = builder.get_object('slot_type_gpu')

        # Queue list
        self.queue_tree = builder.get_object('queue_tree')
        self.queue_list = builder.get_object('queue_list')

        # Info
        self.info = builder.get_object('info_alignment')

        # Log
        self.log_view = builder.get_object('log_text_view')
        self.log_view.modify_font(self.mono_font)
        self.log = builder.get_object('log_buffer')
        self.log.create_mark('end', self.log.get_end_iter())
        self.log_severity = builder.get_object('log_severity')
        self.log_slot_enable = builder.get_object('log_slot_enable')
        self.log_slot = builder.get_object('log_slot')
        self.log_unit_enable = builder.get_object('log_unit_enable')
        self.log_unit = builder.get_object('log_unit')
        self.log_follow = builder.get_object('log_follow')

        # Widget maps
        self.client_entries = WidgetMap(self.client_dialog, '_entry')
        self.client_option_widgets = \
            WidgetMap(self.client_config_notebook, '_option')
        self.client_config_tabs = WidgetMap(self.client_config_notebook, '_tab')
        self.slot_option_widgets = WidgetMap(self.slot_dialog, '_option')
        roots = [self.window, self.client_dialog]
        self.preference_widgets = WidgetMap(self.preferences_dialog, '_pref')
        widget = builder.get_object('advanced_unit_frame')
        self.queue_widgets = WidgetMap(widget, None, 'queue_')

        # Stats prefs
        self.donor_stats_pref = self.preference_widgets['donor_stats']
        self.team_stats_pref = self.preference_widgets['team_stats']
        self.donor_stats_list = builder.get_object('donor_stats_links_list')
        map(self.donor_stats_list.append, self.donor_stats_links)
        self.team_stats_list = builder.get_object('team_stats_links_list')
        map(self.team_stats_list.append, self.team_stats_links)

        # OSX integration
        if sys.platform == 'darwin':
            # Setup dock menu
            self.osx_menu = builder.get_object('osx_tray_menu')
            if self.is_old_gtk:
                self.osx_app.set_dock_menu(self.osx_menu)
            else:
                self.osx_create_dock_menu(self.osx_menu)

            # Create application menu
            self.osx_menubar = gtk.MenuBar()
            self.osx_menubar.show_all()
            self.osx_app.set_menu_bar(self.osx_menubar)
            if self.is_old_gtk:
                self.osx_group = self.osx_app.add_app_menu_group()
                self.osx_menu.foreach(self.osx_add_to_menu)
            else:
                self.osx_create_app_menu(self.osx_menu)

            # Hide some widgets in OSX
            for name in ['ui_pref_frame', 'theme_pref', 'theme_label']:
                widget = builder.get_object(name)
                widget.set_property('visible', False)

            if self.osx_version >= (10,7):
                # remove broken window resize grip
                self.status_bar.set_property('has-resize-grip', False)
                self.time_label.set_property('xpad', 6)
            else:
                self.time_label.set_property('xpad', 2)

        # Validators
        EntryValidator(self, self.client_option_widgets['user'], r'^[!-~]+$',
                       'User name must be a non-empty string containing only '
                       'alphanumeric characters, standard punctuation and '
                       'no white-space.')

        self.passkey_validator = \
            PasswordValidator(self, builder.get_object('passkey_option'),
                              builder.get_object('passkey_reenter'),
                              builder.get_object('passkey_valid_image'),
                              builder.get_object('passkey_valid_text'),
                              r'^[0-9a-fA-F]{0,32}$', 'The passkey must be a '
                              '32 character hexadecimal string.')

        self.password_validator = \
            PasswordValidator(self, builder.get_object('password_option'),
                              builder.get_object('password_reenter'),
                              builder.get_object('password_valid_image'),
                              builder.get_object('password_valid_text'))

        self.proxy_pass_validator = \
            PasswordValidator(self, builder.get_object('proxy_pass_option'),
                              builder.get_object('proxy_pass_reenter'),
                              builder.get_object('proxy_pass_valid_image'),
                              builder.get_object('proxy_pass_valid_text'))

        # Fix client port default
        port = builder.get_object('port_adjustment')
        port.set_value(36330)

        # Connect signals
        builder.connect_signals(self)
        self.builder = builder = None # Discard builder

        self.client_dialog.client = None

        # Load
        self.preferences_load()
        self.load_clients()

        # If we don't have any clients add the default client
        if not len(self.clients):
            client = Client(self, 'local', '127.0.0.1', 36330, '')
            self.add_client(client)
            self.save_clients()

        # Select first client
        self.select_first_client()

        # Start client notebook deactivated
        self.deactivate_client()

        self.window.connect('notify::is-active', self.on_window_is_active)


    # Main loop
    def run(self):
        self.quitting = False

        if sys.platform != 'darwin':
            self.check_clients() # Slightly faster load?

        self.restore()

        self.set_update_timer_interval(100)

        if sys.platform == 'darwin':
            # reduce updates to 2Hz after 30 seconds
            gobject.timeout_add(30000, self.set_update_timer_interval, 500)

            # OSX signals
            self.osx_app.connect('NSApplicationDidBecomeActive',
                                 self.app_did_become_active)
            self.osx_app.connect('NSApplicationWillTerminate',
                                 self.app_will_terminate)
            self.osx_app.connect('NSApplicationBlockTermination',
                                 self.app_should_block_terminate)

            self.osx_app.ready()

            if self.osx_version >= (10,7) and self.osx_version < (10,9):
                self.osx_window_focus_workaround()

            try:
                # add cmd-w and cmd-m to window
                # cmd-w would need to be same as cancel for dialogs
                ag = gtk.AccelGroup()
                self.window_accel_group = ag
                key, mod = gtk.accelerator_parse("<meta>w")
                ag.connect_group(key, mod, gtk.ACCEL_VISIBLE,
                                 osx_accel_window_close)
                key, mod = gtk.accelerator_parse("<meta>m")
                ag.connect_group(key, mod, gtk.ACCEL_VISIBLE,
                                 osx_accel_window_minimize)
                self.window.add_accel_group(ag)
            except Exception as e:
                print (e)

        gtk.main()


    # Util
    def osx_add_to_menu(self, widget):
        if isinstance(widget, gtk.SeparatorMenuItem):
            self.osx_group = self.osx_app.add_app_menu_group()

        elif isinstance(widget, gtk.MenuItem):
            name = widget.child.get_text()

            def activate_item(widget, target):
                target.emit('activate')

            item = gtk.MenuItem(name)
            item.show()
            item.connect('activate', activate_item, widget)
            self.osx_app.add_app_menu_item(self.osx_group, item)


    def osx_create_app_menu(self, widgets):
        i = 0
        for widget in widgets:
            if not isinstance(widget, gtk.SeparatorMenuItem):
                def activate_item(widget, target):
                    target.emit('activate')
                label = widget.get_label()
                item = gtk.MenuItem(label)
                item.show()
                item.connect('activate', activate_item, widget)
            self.osx_app.insert_app_menu_item(widget, i)
            i += 1


    def osx_create_dock_menu(self, widgets):
        menu = gtk.Menu()
        for widget in widgets:
            if isinstance(widget, gtk.SeparatorMenuItem):
                item = gtk.SeparatorMenuItem()
            else:
                def activate_item(widget, target):
                    target.emit('activate')
                label = widget.get_label()
                item = gtk.MenuItem(label)
                item.connect('activate', activate_item, widget)
            menu.append(item)
        menu.show_all()
        self.osx_app.set_dock_menu(menu)
        # retain menu, or it won't work
        self.osx_dock_menu = menu


    def osx_window_focus_workaround(self):
        # osx 10.7+, part of Trac #793, not resolved by gtk 2.24.10
        # only thing that works is clicking FAHControl icon in Dock
        # this is the equivalent
        # must be backgrounded so app can process reopen event
        # and not deadlock waiting for osascript
        cmd = ['/usr/bin/osascript', '-e', 'tell app "FAHControl" to reopen']
        try:
            subprocess.Popen(cmd)
        except Exception as e:
            print (e, ':', ' '.join(cmd))


    def connect_option_cell(self, name, model, col):
        cell = self.builder.get_object(name)
        cell.connect('edited', self.on_option_edit, model, col)


    def connect_option_view(self, prefix):
        tree = self.builder.get_object(prefix + 'option_tree_view')
        model = self.builder.get_object(prefix + 'option_list')

        self.connect_option_cell(prefix + 'option_name_cell', model, 0)
        self.connect_option_cell(prefix + 'option_value_cell', model, 1)

        return tree, model

    # Timer functions
    def set_update_timer_interval(self, interval = None):
        if self.timer_id is not None:
            glib.source_remove(self.timer_id)
            self.timer_id = None
        if interval and int(interval) > 0:
            self.timer_id = gobject.timeout_add(interval, self.on_timer)
        return False # stop if timer callback


    def check_clients(self):
        # Make sure there is a selected client
        if not len(self.selected_clients): self.select_first_client()

        # Update clients
        for client in self.clients.values(): client.update(self)

        # (De)activate client
        if self.active_client:
            if not self.active_client.is_updated():
                self.deactivate_client()

        else: self.activate_client() # Try to activate

        # Check if active and online
        if self.active_client and self.active_client.is_online():
            self.client_notebook.set_sensitive(True)
        else: self.client_notebook.set_sensitive(False)

        # Update status bar
        if self.status_clear_time and self.status_clear_time < time.time():
            self.status_bar.pop(0)
            self.status_clear_time = None


    def on_timer(self):
        try:
            # Update clock
            now = time.time()
            if self.last_clock and self.last_clock != now:
                s = time.strftime('UTC: %Y-%m-%dT%H:%M:%SZ', time.gmtime())
                self.time_label.set_text(s)

                # Update ppd
                ppd = 0
                for client in self.clients.values(): ppd += client.ppd
                label = 'Total Estimated Points Per Day: '
                if int(ppd): label += '%d' % int(ppd)
                else: label += 'Unknown'
                self.ppd_label.set_text(label)

            self.last_clock = now

            self.check_clients()
            self.viewer_check()

            if self.exit_requested.isSet():
                self.quit()

            if self.ping.isSet():
                self.ping.clear()
                self.restore()

            if 2.5 < now - self.last_db_flush:
                self.last_db_flush = time.time()
                self.db.flush_queued()

        except:
            traceback.print_exc()

        return True # Keep running


    # Actions
    def quit(self):
        if self.quitting: return
        self.quitting = True

        gtk.main_quit()

        self.viewer_close()

        self.set_update_timer_interval(0)

        for client in self.clients.values(): client.close()

        try:
            self.db.flush_queued()
        except Exception as e:
            print (e)

        sys.exit(0) # Force shutdown


    def set_status(self, text):
        self.status_bar.pop(0)
        self.status_bar.push(0, text)
        self.status_clear_time = time.time() + 10


    # OSX signals
    def app_did_become_active(self, app):
        self.restore()


    def app_will_terminate(self, app):
        # Calxalot: Probably don't need both this and should_block, but I can
        # imagine the app quitting without asking.  Note that if we reach this,
        # we exit after quit() and never return to run()
        self.quit()


    def app_should_block_terminate(self, app):
        self.quit()
        return False


    # Preference methods
    def load_theme(self, theme):
        for name, rc in self.theme_list:
            if theme == name:
                print ('Loading theme %r' % theme)

                settings = gtk.settings_get_default()

                if rc is None:
                    settings.set_property('gtk-theme-name', self.system_theme)
                    gtk.rc_set_default_files([])
                else:
                    settings.set_property('gtk-theme-name', theme)
                    gtk.rc_set_default_files([rc])

                gtk.rc_reparse_all_for_settings(settings, True)
                gtk.rc_reset_styles(settings)

                break


    def load_themes(self):
        paths = get_theme_dirs()
        unique = set()
        list = []
        default_rc = None

        for path in paths:
            if not os.path.exists(path): continue
            for name in os.listdir(path):
                if name in unique: continue
                rc = path + '/' + name + '/gtk-2.0/gtkrc'
                if os.path.exists(rc):
                    unique.add(name)
                    if sys.platform == 'win32' and \
                            name == 'Windows-Default' and default_rc is None:
                        default_rc = rc
                    else: list.append([name, rc])

        list.sort(key = lambda x: x[0])

        return [['Default', default_rc]] + list


    def get_pref(self, name):
        widget = self.preference_widgets[name]
        return get_widget_str_value(widget)


    def get_viz_render_mode(self):
        value = self.get_pref('viz_render_mode')

        if value == 'Space Filling': return 1
        if value == 'Ball And Stick': return 2
        if value == 'Stick': return 3
        if value == 'Advanced Space Filling': return 4
        if value == 'Advanced Ball And Stick': return 5
        if value == 'Advanced Stick': return 6
        if value == 'Cartoon Space Filling': return 7
        if value == 'Cartoon Ball And Stick': return 8

        return 1


    def preferences_set(self):
        # URLs
        for pref in ['donor', 'team']:
            entry = self.preference_widgets[pref + '_stats']
            combo = self.preference_widgets[pref + '_stats_link']
            button = getattr(self, pref + '_info')

            link = self.get_pref(pref + '_stats_link')
            custom_uri = self.get_pref(pref + '_stats')
            entry.set_text(custom_uri)

            if link == 'Custom': button.set_uri(custom_uri)
            else:
                model = combo.get_model()
                iter = model.get_iter_first()
                while iter is not None:
                    if model.get_value(iter, 0) == link:
                        combo.set_active_iter(iter)
                        button.set_uri(model.get_value(iter, 1))
                        break
                    iter = model.iter_next(iter)


    def preferences_load(self):
        # Preferences dialog
        for name, widget in self.preference_widgets.items():
            value = None

            if self.db.has(name):
                value = self.db.get(name)
                if name == 'theme': self.load_theme(value)

            elif name == 'theme': value = 'Default'
            elif name == 'viz_command': value = 'FAHViewer'
            elif name == 'viz_fullscreen': value = 'False'
            elif name == 'viz_width': value = '800'
            elif name == 'viz_height': value = '600'
            elif name == 'viz_render_mode': value = 'Advanced Space Filling'
            elif name == 'viz_cycle_snapshots': value = 'True'
            elif name == 'donor_stats': value = ''
            elif name == 'team_stats': value = ''
            elif name == 'donor_stats_link': value = 'Folding@home'
            elif name == 'team_stats_link': value = 'Folding@home'
            else: raise Exception('Unknown preference widget "%s"' % name)

            if value is not None: set_widget_str_value(widget, value)

        # Update
        self.preferences_set()


    def preferences_dialog_init(self):
        for name, widget in self.preference_widgets.items():
            if self.db.has(name):
                value = self.db.get(name)
                set_widget_str_value(widget, value)

        for pref in ['donor', 'team']:
            entry = self.preference_widgets[pref + '_stats']
            combo = self.preference_widgets[pref + '_stats_link']
            entry.set_sensitive(combo.get_active_text() == 'Custom')


    def preferences_save(self):
        for name, widget in self.preference_widgets.items():
            value = get_widget_str_value(widget)
            if value is None: self.db.clear(name, False)
            else: self.db.set(name, value, False)

        self.db.commit()


    # Client methods
    def select_first_client(self):
        iter = self.client_list.get_iter_first()
        if iter: self.client_tree.get_selection().select_iter(iter)


    def activate_client(self):
        if self.active_client: return
        if not len(self.selected_clients): return

        # Check that all selected clients are active
        for client in self.selected_clients:
            if not client.is_updated(): return

        # Activate client(s)
        for client in self.selected_clients:
            self.active_client = client
            self.active_client.update_status_ui(self)
            break # TODO only supporting one active client right now

        self.last_clients_update = 0
        self.update_client_status()


    def deactivate_client(self):
        if self.active_client:
            self.active_client.reset_status_ui(self)
            self.active_client = None

        self.client_label.set_markup('<b>Client: inactive</b>')
        self.update_client_status()


    def update_client_status(self):
        if len(self.selected_clients):
            client = list(self.selected_clients)[0]

            text = '<b>Client: %s' % client.name
            status = client.get_status()
            color = status_to_color(status)
            text += ' <span background="%s">%s</span></b>' % (color, status)

            if self.active_client and self.active_client.config.get_running():
                text += ' Running'
            else: text += ' Inactive'

        else: text = '<b>Client: no client selected</b>'

        self.client_label.set_markup(text)
        if self.client_dialog.client is not None:
            self.client_config_label.set_markup(text)


    def save_clients(self):
        self.db.delete('clients')

        for client in self.clients.values():
            client.save(self.db)

        self.db.commit()


    def update_client_list(self):
        # update all rows, whether selected/active or not
        try:
            iter = self.client_list.get_iter_first()
            while iter is not None:
                name = self.client_list.get_value(iter, 0)
                client = self.clients.get(name)
                if client is not None:
                    path = self.client_list.get_path(iter)
                    row = client.get_row(self)
                    for i in range(len(row)):
                        self.client_list.set(iter, i, row[i])
                    self.client_list.row_changed(path, iter)
                iter = self.client_list.iter_next(iter)
        except Exception as e:
            print (e)
        return False # no timer repeat


    def resort_client_list(self):
        ibyname_old = {}
        iter = self.client_list.get_iter_first()
        i = 0
        while iter is not None:
            name = self.client_list.get_value(iter, 0)
            ibyname_old[name] = i
            iter = self.client_list.iter_next(iter)
            i += 1
        new_order = []
        for client in self.sorted_clients():
            name = client.name
            i = ibyname_old.get(name)
            if i is None:
                print ('unable to resort client list: unknown name %s' % name)
                return
            new_order.append(i)
        self.client_list.reorder(new_order)
        return False # don't repeat if timer callback


    def sorted_clients(self, unsorted_clients = None):
        if unsorted_clients is None:
            unsorted_clients = self.clients.values()

        # pre-sort by client.name
        clients = sorted(unsorted_clients, key=lambda c: c.name)

        # sort local clients first
        group0 = [] # client "local" (should only be one, currently)
        group1 = [] # other is_local clients (should not be any, currently)
        group2 = [] # localhost clients starting with "local"
        group3 = [] # other localhost clients
        group4 = [] # remote clients (and any local referenced by host name)

        for client in clients:
            is_local = client.is_local()
            is_local_addr = client.address in ['localhost','127.0.0.1']

            if is_local and client.name == 'local':
                group0.append(client)
            elif is_local:
                group1.append(client)
            elif is_local_addr and client.name.startswith('local'):
                group2.append(client)
            elif is_local_addr:
                group3.append(client)
            else:
                group4.append(client)

        return group0 + group1 + group2 + group3 + group4


    def load_clients(self):
        clients = []
        for row in self.db.select('clients', orderby = 'name'):
            client = Client(self,
                row['name'], row['address'], int(row['port']), row['password'])
            clients.append(client)

        for client in self.sorted_clients(clients):
            self.add_client(client)


    def clear_clients(self):
        for client in self.clients: client.close()
        self.clients.clear()
        self.clientsByName.clear()
        self.client_list.clear()


    def save_client_config(self, client):
        try:
            options, slots = client.config.get_changes(self)
            if not (options or slots != ([], [], [])): return True

            # Validate passkey
            if not self.passkey_validator.is_good():
                raise Exception('Passkey is invalid')

            # Validate password
            if not self.password_validator.is_good():
                raise Exception('Client password is invalid')

            # Validate proxy password
            if not self.proxy_pass_validator.is_good():
                raise Exception('Proxy password is invalid')

            self.deactivate_client()

            self.set_status('Saving...')

            for client in self.selected_clients:
                # TODO check returned error count
                client.save_config(options, slots)
                client.update(self) # Slightly faster save

                # Update password if changed on client
                if 'password' in options:
                    client.set_password(options['password'])
                if 'password!' in options: client.set_password('')

            return True

        except Exception, msg:
            self.set_status('Save Failed')
            self.error(msg)
            return False


    def check_duplicate_client_name(self, name):
        if name in self.clients:
            self.error('Client with name "%s" is already in client list' % name)
            return True
        return False


    def check_duplicate_client_address(self, address):
        if address in self.clientsByAddress:
            self.error('Client with address "%s" is already in client list' %
                       address)
            return True
        return False


    def update_client(self, client, name, address, port, password):
        reload = False
        old_name = client.name

       # Check for duplicates
        if client.name != name:
            if self.check_duplicate_client_name(name): return False

        new_address = Client.make_address(address, port)
        if client.get_address() != new_address:
            if self.check_duplicate_client_address(new_address): return False

        # Update
        if client.name != name:
            del self.clients[client.name]
            client.name = name
            self.clients[name] = client

        if client.get_address() != new_address:
            del self.clientsByAddress[client.get_address()]
            client.set_address(address, port)
            self.clientsByAddress[new_address] = client
            reload = True

        if client.get_password() != password:
            client.set_password(password)
            reload = True

        # Update client row
        row = client.get_row(self)

        # Find client in client_list
        iter = self.client_list.get_iter_first()
        while iter is not None:
            if old_name == self.client_list.get_value(iter, 0):
                path = self.client_list.get_path(iter)

                for i in range(len(row)):
                    self.client_list.set(iter, i, row[i])
                self.client_list.row_changed(path, iter)

                break

            iter = self.client_list.iter_next(iter)

        # Reload
        if reload:
            client.reconnect()
            self.deactivate_client()

        return True


    def add_client(self, client):
        name = client.name
        address = client.get_address()

        # Check for duplicates
        if self.check_duplicate_client_name(name): return False
        if self.check_duplicate_client_address(address): return False

        # Add it
        self.clients[name] = client
        self.clientsByAddress[address] = client
        self.client_list.append(client.get_row(self))

        return True


    def remove_client(self, client):
        client.close()
        del self.clients[client.name]
        del self.clientsByAddress[client.get_address()]
        if client is self.active_client: self.active_client = None


    def remove_client_path(self, path, iter):
        name = self.client_list.get(iter, 0)[0]
        self.remove_client(self.clients[name])


    def get_selected_clients(self):
        selection = get_tree_selection(self.client_tree)
        names = map(lambda item: self.client_list.get(item[1], 0)[0], selection)
        return set(map(self.clients.get, names))


    def edit_client(self, client):
        self.client_dialog.client = client
        self.update_client_status()
        client.load_dialog(self)

        if self.active_client and self.active_client.is_online():
            for name, widget in self.client_config_tabs.items(): widget.show()
            self.client_dialog.config_hidden = False

        else:
            for name, widget in self.client_config_tabs.items():
                if name != 'connection': widget.hide()
            self.client_dialog.config_hidden = True

        self.open_dialog(self.client_dialog)


    def open_dialog(self, dialog):
        # Hack to make WrapLabel work
        dims = dialog.get_size()
        dialog.resize(dims[0] + 1, dims[1] + 1)
        dialog.present()
        dialog.resize(*dims)


    # Slot methods
    def get_selected_slot_ids(self):
        selection = get_tree_selection(self.slot_status_tree)
        ids = map(lambda x: int(self.slot_status_list.get(x[1], 0)[0]),
                  selection)
        return ids


    # Window methods
    def get_visible_dialogs(self):
        dialogs = []
        for dialog in self.dialogs:
            if dialog.flags() & gtk.MAPPED:
                dialogs.append(dialog)

        return dialogs


    def hide_all_windows(self):
        self.restore_dialogs = self.get_visible_dialogs()
        for dialog in self.restore_dialogs: dialog.hide()
        self.window.hide()
        self.window_visible = False


    def restore(self):
        self.window.present()
        self.window.deiconify()
        self.window_visible = True

        if sys.platform == 'darwin':
            # restore osx minimized dialogs
            for dialog in self.get_visible_dialogs():
                dialog.present()

        # Restore dialogs
        for dialog in self.restore_dialogs: dialog.present()
        self.restore_dialogs = []


    # Messages
    def close_error_dialog(self, dialog, id = None, data = None):
        dialog.destroy()
        self.error_dialog = None


    def error(self, message, buttons = gtk.BUTTONS_OK, on_response = None,
              on_response_data = None):
        message = str(message)

        # log to terminal window
        if sys.exc_info()[2]: traceback.print_exc()
        print ('ERROR: %s' % message)

        # Don't open more than one
        if self.error_dialog is not None: return False

        if sys.exc_info()[1]: message += '\n%s' % sys.exc_info()[1]

        # create an error message dialog and display modally to the user
        dialog = \
            gtk.MessageDialog(None,
                              gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                              gtk.MESSAGE_ERROR, buttons, message)

        dialog.connect('close', self.close_error_dialog)
        if on_response is not None:
            dialog.connect('response', on_response, on_response_data)
        dialog.connect('response', self.close_error_dialog)
        dialog.set_transient_for(self.window)

        self.error_dialog = dialog
        dialog.show()

        return True


    # Property signals
    def store_property(self, widget, property, name):
        self.db.set(name, widget.get_property(property.name), queue = True)


    def store_dimensions(self, widget, event, name):
        x, y, width, height = widget.get_allocation()
        if 0 <= width and 0 <= height:
            self.db.set(name + '_width', width, queue = True);
            self.db.set(name + '_height', height, queue = True);


    # Action signals
    def on_quit(self, widget, data = None):
        self.quit()


    def on_preferences(self, widget, data = None):
        # OSX crashes with out this, but it's a good idea anyway
        if not self.window_visible: self.restore()

        if self.get_visible_dialogs(): return

        self.preferences_dialog_init()
        self.preferences_dialog.present()


    def viewer_check(self):
        if self.viewer is not None and self.viewer.poll() is not None:
            if self.viewer.returncode and sys.platform == 'darwin':
                self.error('Failed to launch viewer:\n\n' +
                           self.viewer.stderr.read())
            self.viewer = None # Viewer exited


    def viewer_close(self):
        if self.viewer is not None:
            try:
                self.viewer.kill()
                self.viewer.wait() # Note: This could cause a hang kill() fails
            except: pass

            self.viewer = None


    def on_viewer(self, widget, data = None):
        self.viewer_close()

        # Get preferences
        command = self.get_pref('viz_command')
        fullscreen = parse_bool(self.get_pref('viz_fullscreen'))
        width = self.get_pref('viz_width')
        height = self.get_pref('viz_height')
        mode = self.get_viz_render_mode()
        cycle_snapshots = self.get_pref('viz_cycle_snapshots')

        # Create command line
        cmd = shlex.split(command)

        if not (len(cmd) and len(cmd[0])): cmd = ['FAHViewer']

        if sys.platform == 'darwin':
            cmd = ['/usr/bin/open', '-a', cmd[0], '--args'] + cmd[1:]

        if fullscreen: cmd.append('--fullscreen')
        cmd.append('--width=' + width)
        cmd.append('--height=' + height)
        cmd.append('--mode=%d' % mode)
        cmd.append('--cycle-snapshots=' + cycle_snapshots)

        if self.active_client and self.active_client.is_online():
            address = self.active_client.address
            port = self.active_client.port
            cmd.append('--connect=%s:%d' % (address, port))

            password = self.active_client.password
            if password: cmd.append('--password="%s"' % password)

            slot = self.active_client.get_selected_slot(self)
            if slot is not None: cmd.append('--slot=%d' % slot.id)

        debug = True
        if debug: print (cmd)

        try:
            if sys.platform == 'darwin':
                self.viewer = subprocess.Popen(cmd, cwd = get_home_dir(),
                                bufsize = 4096, stderr=subprocess.PIPE)
            else:
                self.viewer = subprocess.Popen(cmd, cwd = get_home_dir())
        except Exception:
            self.error('Failed to launch viewer with command:\n\n' +
                       ' '.join(cmd))


    def on_about(self, widget, data = None):
        # OSX crashes with out this, but it's a good idea anyway
        if not self.window_visible: self.restore()

        if self.get_visible_dialogs(): return False

        self.open_dialog(self.about_dialog)


    def on_about_close(self, widget, data = None):
        self.about_dialog.hide()
        return True # Cancel event


    # Window signals
    def on_window_destroy(self, widget, data = None):
        if sys.platform == 'darwin':
            self.hide_all_windows()
            return True # prevent destroy
        self.quit()


    def on_window_delete(self, widget, event, data = None):
        return self.on_window_destroy(widget)


    def on_window_is_active(self, window, *args):
        try:
            if window.is_active(): self.update_client_list()
        except Exception as e: print (e)


    # Preferences signals
    def on_preferences_ok(self, widget, data = None):
        self.preferences_set()
        self.preferences_save()
        self.preferences_dialog.hide()


    def on_preferences_cancel(self, widget, data = None):
        # Reset theme
        if self.db.has('theme'): current_theme = self.db.get('theme')
        else: current_theme = 'Default'
        if self.get_pref('theme') != current_theme:
            self.load_theme(current_theme)

        # FIXME workaround for defect: get_pref takes from dialog widgets
        self.preferences_dialog_init()
        self.preferences_dialog.hide()
        return True # Cancel event


    def on_theme_pref_changed(self, widget, data = None):
        iter = widget.get_active_iter()
        theme = widget.get_model().get_value(iter, 0)
        self.load_theme(theme)


    # Proxy signals
    def on_proxy_enable_toggled(self, widget, data = None):
        self.proxy_frame.set_sensitive(widget.get_active())
        self.proxy_auth_frame.set_sensitive(widget.get_active())


    # Client list signals
    def on_client_add_button_clicked(self, widget, data = None):
        if self.get_visible_dialogs(): return

        # Make client name
        for i in xrange(sys.maxint):
            name = 'client%d' % i
            if not name in self.clients: break

        self.client_entries['name'].set_text(name)

        self.client_dialog.client = None
        text = 'Configure New Client Connection'
        self.client_config_label.set_markup(text)

        # Reset dialog
        self.client_entries['name'].set_sensitive(True)
        self.client_entries['address'].set_sensitive(True)
        for name, widget in self.client_config_tabs.items():
            if name != 'connection': widget.hide()

        self.open_dialog(self.client_dialog)


    def on_client_remove_button_clicked(self, widget, data = None):
        remove_tree_selection(self.client_tree, self.remove_client_path)
        self.save_clients()


    def on_configure(self, widget, data = None):
        if self.get_visible_dialogs(): return

        selection = get_tree_selection(self.client_tree)
        if not len(selection): return
        name = self.client_list.get(selection[0][1], 0)[0]
        client = self.clients[name]
        self.edit_client(client)


    def on_client_tree_view_row_activated(self, widget, path, col, data = None):
        if self.get_visible_dialogs(): return

        iter = self.client_list.get_iter(path)
        name = self.client_list.get(iter, 0)[0]
        client = self.clients[name]
        self.edit_client(client)


    def on_client_selection_changed(self, widget, data = None):
        self.deactivate_client()

        self.selected_clients = self.get_selected_clients()

        # Modify selection
        for client in self.clients.values():
            client.set_selected(client in self.selected_clients)

        self.update_client_status()

        if len(self.clients): self.activate_client()

        self.update_client_list()
        gobject.timeout_add(5000, self.update_client_list)

        # temporarily increase update rate for faster switch
        if sys.platform == 'darwin':
            self.set_update_timer_interval(100)
            gobject.timeout_add(10000, self.set_update_timer_interval, 500)


    # Client options list signals
    def on_client_options_add_button_clicked(self, widget, data = None):
        self.option_present(self.option_list, self.client_dialog)


    def on_client_options_remove_button_clicked(self, widget, data = None):
        remove_tree_selection(self.option_tree)


    # Core options list signals
    def on_core_options_add_button_clicked(self, widget, data = None):
        self.core_option_entry.set_text('')
        self.core_options_dialog.set_transient_for(self.client_dialog)
        self.core_options_dialog.present()


    def on_core_options_remove_button_clicked(self, widget, data = None):
        remove_tree_selection(self.core_option_tree)


    def on_core_options_ok(self, widget, data = None):
        option = self.core_option_entry.get_text().strip()
        if not option:
            self.error('Invalid option')
            return

        self.core_option_list.append([option])
        self.core_options_dialog.hide()


    def on_core_options_cancel(self, widget, data = None):
        self.core_options_dialog.hide()
        return True # Cancel event


    # Client dialog signals
    def on_client_ok(self, widget, data = None):
        name = self.client_entries['name'].get_text()
        address = self.client_entries['address'].get_text()
        port = self.client_entries['port'].get_text()
        password = self.client_entries['password'].get_text()

        if not name:
            self.error('Invalid name')
            return

        if not address:
            self.error('Invalid address')
            return

        if not port:
            self.error('Invalid port')
            return

        port = int(port)

        if self.client_dialog.client: # Existing client
            client = self.client_dialog.client
            config_hidden = self.client_dialog.config_hidden

            # Save client options
            if config_hidden or self.save_client_config(client):
                # Save client connection
                if self.update_client(client, name, address, port, password):
                    self.save_clients()
                    self.client_dialog.hide()
                    self.resort_client_list()

        else: # New client
            client = Client(self, name, address, port, password)
            if self.add_client(client):
                self.save_clients()
                self.client_dialog.hide()
                self.resort_client_list()


    def on_client_cancel(self, widget, data = None):
        self.client_dialog.hide()
        return True # Cancel event


    # Folding power signals
    def on_fold_button_clicked(self, widget, data = None):
        self.active_client.unpause()


    def on_pause_button_clicked(self, widget, data = None):
        self.active_client.pause()


    def on_finish_button_clicked(self, widget, data = None):
        self.active_client.finish()


    def on_folding_power_change_value(self, widget, scroll, value, data = None):
        # Clamp slider to integer increments
        value = int(round(value))
        if self.folding_power.get_value() != value:
            self.folding_power.set_value(value)
        return True


    def on_folding_power_value_changed(self, widget, data = None):
        if not self.folding_power_changing and self.active_client:
            power = self.folding_power_levels[int(widget.get_value())]
            self.active_client.set_power(power)


    def on_folding_power_button_press(self, widget, data = None):
        self.folding_power_changing = True


    def on_folding_power_button_release(self, widget, data = None):
        if self.active_client:
            power = self.folding_power_levels[int(widget.get_value())]
            self.active_client.set_power(power)

        self.folding_power_changing = False


    # User status signals
    def on_team_stats_link_changed(self, widget, data = None):
        iter = widget.get_active_iter()
        model = widget.get_model()
        text = model.get_value(iter, 0)
        self.team_stats_pref.set_sensitive(text == 'Custom')


    def on_donor_stats_link_changed(self, widget, data = None):
        iter = widget.get_active_iter()
        model = widget.get_model()
        text = model.get_value(iter, 0)
        self.donor_stats_pref.set_sensitive(text == 'Custom')


    # Queue tree signals
    def on_queue_tree_cursor_changed(self, widget, data = None):
        if self.active_client:
            self.active_client.config.select_queue_slot(self)


    # Slot list signals
    def on_slot_add_button_clicked(self, widget, data = None):
        SlotConfig.clear_dialog(self)
        self.slot_dialog.slot_iter = None
        self.open_dialog(self.slot_dialog)


    def on_slot_remove_button_clicked(self, widget, data = None):
        remove_tree_selection(self.slot_tree)


    def on_slot_edit_button_clicked(self, widget, data = None):
        selection = get_tree_selection(self.slot_tree)

        if selection:
            iter = selection[0][1]
            slot = self.slot_list.get(iter, 2)[0].slot
            slot.load_dialog(self)
            self.slot_dialog.slot_iter = iter
            self.open_dialog(self.slot_dialog)


    def on_slot_tree_view_row_activated(self, widget, path, col, data = None):
        iter = self.slot_list.get_iter(path)
        slot = self.slot_list.get(iter, 2)[0].slot
        slot.load_dialog(self)
        self.slot_dialog.slot_iter = iter
        self.open_dialog(self.slot_dialog)



    # Slot dialog signals
    def on_slot_ok(self, widget, data = None):
        if self.slot_dialog.slot_iter is None:
            slot = SlotConfig()
            slot.save_dialog(self)
            slot.add_to_ui(self) # Add to list

        else:
            iter = self.slot_dialog.slot_iter
            id, type, wrapper = self.slot_list.get(iter, 0, 1, 2)
            slot = wrapper.slot
            slot.save_dialog(self)
            if slot.type != type: self.slot_list.set(iter, 1, slot.type)

        self.slot_dialog.hide()


    def on_slot_cancel(self, widget, data = None):
        self.slot_dialog.hide()
        return True # Cancel event


    # Slot options list signals
    def on_slot_options_add_button_clicked(self, widget, data = None):
        self.option_present(self.slot_option_list, self.slot_dialog)


    def on_slot_options_remove_button_clicked(self, widget, data = None):
        remove_tree_selection(self.slot_option_tree)


    # Options edit
    def check_option_name(self, name):
        if not re.match(r'^[a-zA-Z][\w-]*$', name):
            self.error('Invalid option name.')
            return False
        return True


    def on_option_edit(self, cell, path, text, model, column):
        if column == 0 and not self.check_option_name(text): return
        if model[path][column] != text: model[path][column] = text


    def on_core_option_cell_edited(self, cell, path, text, data = None):
        if not text:
            self.error('Invalid option')
            return
        if self.core_option_list[path][0] != text:
            self.core_option_list[path][0] = text


    # Options dialog signals
    def option_present(self, model, parent):
        self.option_name_entry.set_text('')
        self.option_value_entry.set_text('')
        self.options_dialog.option_model = model
        self.options_dialog.set_transient_for(parent)
        self.options_dialog.present()


    def on_options_ok(self, widget, data = None):
        name = self.option_name_entry.get_text().strip()
        value = self.option_value_entry.get_text()

        if not self.check_option_name(name): return

        self.options_dialog.option_model.append([name, value])
        self.options_dialog.hide()


    def on_options_cancel(self, widget, data = None):
        self.options_dialog.hide()
        return True # Cancel event


    # Configure dialog signals
    def on_configure_ok(self, widget, data = None):
        self.configure_dialog.hide()
        if self.active_client:
            # Select identity tab
            self.client_config_notebook.set_current_page(1)
            self.edit_client(self.active_client)
        return True # Cancel event


    def on_configure_cancel(self, widget, data = None):
        self.configure_dialog.hide()
        if self.active_client:
            # Fold anonymously
            self.active_client.conn.queue_command('save')
        return True # Cancel event


    # Slot status tree signals
    def on_slot_status_tree_cursor_changed(self, widget, data = None):
        if self.active_client:
            self.active_client.config.select_slot(self)


    def on_slot_status_tree_view_button_release_event(self, widget, event,
                                                      data = None):
        if event.button != 3: return
        idle = self.active_client.get_selected_slot(self).idle
        self.idle_slot_item.set_active(idle)
        self.slot_menu.popup(None, None, None, button = event.button,
                             activate_time = event.time, data = data)


    def on_unpause_slot_item_activate(self, widget, data = None):
        for id in self.get_selected_slot_ids():
            self.active_client.unpause(id)


    def on_pause_slot_item_activate(self, widget, data = None):
        for id in self.get_selected_slot_ids():
            self.active_client.pause(id)


    def on_idle_slot_item_toggled(self, widget, data = None):
        for id in self.get_selected_slot_ids():
            if widget.get_active(): self.active_client.on_idle(id)
            else: self.active_client.always_on(id)


    def on_finish_slot_item_activate(self, widget, data = None):
        for id in self.get_selected_slot_ids():
            self.active_client.finish(id)


    # Log signals
    def on_download_log_clicked(self, widget, data = None):
        self.active_client.refresh_log()
        self.log.set_text('')


    def on_copy_log_clicked(self, widget, data = None):
        log = self.log
        text = log.get_text(log.get_start_iter(), log.get_end_iter())
        gtk.Clipboard().set_text(text)


    def on_clear_log_clicked(self, widget, data = None):
        if self.active_client: self.active_client.config.log_clear(self)


    def on_update_log(self, widget, data = None):
        if self.active_client: self.active_client.config.update_log(self)


    # Scale value formatting
    def on_cpu_usage_scale_format_value(self, widget, value, data = None):
        return '%d%%' % value


    def on_checkpoint_scale_format_value(self, widget, value, data = None):
        return '%d min.' % value


    def on_uri_hook(self, widget, url, data = None):
        keys = {'donor': urllib.quote(self.donor_info.get_label()),
                'team': urllib.quote(self.team_info.get_label())}
        webbrowser.open(url % keys)
