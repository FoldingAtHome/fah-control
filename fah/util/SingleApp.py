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

import sys
import socket
import threading
import SocketServer

import gtk

from fah.Icon import get_icon

single_app_host = '127.0.0.1'
single_app_port = 32455
single_app_addr = (single_app_host, single_app_port)


class SingleAppRequestHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        cmd = self.request.recv(1024).strip()

        if cmd == 'PING':
            self.server.ping.set()
            self.request.send('OK\r\n')

        elif cmd == 'EXIT':
            self.server.exit_requested.set()
            self.request.send('OK\r\n')



class SingleAppServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True

    def __init__(self):
        # Check to see if we are already running
        self.check_for_instance()

        self.ping = threading.Event()
        self.exit_requested = threading.Event()

        SocketServer.TCPServer.__init__(
            self, single_app_addr, SingleAppRequestHandler)

        thread = threading.Thread(target = self.serve_forever)
        # Exit the server thread when the main thread terminates
        thread.setDaemon(True)
        thread.start()


    def check_for_instance(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(single_app_addr)
            sock.send('PING')
            if sock.recv(1024).strip() == 'OK':
                print ('Already running')
                sys.exit(1)

        except socket.error:
            # Assume this is the first instance
            return

        finally:
            if sock is not None: sock.close()
