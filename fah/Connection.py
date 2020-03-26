#!/usr/bin/env python2
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

import socket
import select
import errno
import time
import sys
import traceback

from fah.util import OrderedDict

if sys.platform == 'win32':
    from ctypes import windll
    WSAGetLastError = windll.ws2_32.WSAGetLastError

debug = False
WSAEWOULDBLOCK = 10035

class Connection:
    def __init__(self, address = 'localhost', port = 36330, password = None,
                 retry_rate = 5):
        self.address = address
        self.port = int(port)
        self.password = password
        self.init_commands = []
        self.retry_rate = retry_rate

        self.socket = None
        self.reset()


    def set_init_commands(self, commands):
        self.init_commands = commands

        if self.is_connected():
            map(self.queue_command, self.init_commands)


    def get_status(self):
        if self.connected: return 'Online'
        #if self.socket is None: return 'Offline'
        return 'Connecting'


    def is_connected(self):
        if self.socket is None: return False
        if self.connected: return True

        rlist, wlist, xlist = select.select([], [self.socket], [self.socket], 0)

        if len(wlist) != 0: self.connected = True
        elif len(xlist) != 0:
            self.fail_reason = 'refused'
            self.close()

        return self.connected


    def can_write(self):
        rlist, wlist, xlist = select.select([], [self.socket], [], 0)
        return len(wlist) != 0


    def can_read(self):
        rlist, wlist, xlist = select.select([self.socket], [], [], 0)
        return len(rlist) != 0


    def reset(self):
        self.close()
        self.messages = []
        self.readBuf = ''
        self.writeBuf = ''
        self.fail_reason = None
        self.last_message = 0
        self.last_connect = 0


    def open(self):
        self.reset()
        self.last_connect = time.time()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        err = self.socket.connect_ex((self.address, self.port))

        if err != 0 and not err in [
            errno.EINPROGRESS, errno.EWOULDBLOCK, WSAEWOULDBLOCK]:
            self.fail_reason = 'connect'
            raise Exception('Connection failed: ' + errno.errorcode[err])

        if self.password: self.queue_command('auth "%s"' % self.password)
        map(self.queue_command, self.init_commands)


    def close(self):
        if self.socket is not None:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except: pass
            try:
                self.socket.close()
            except: pass
            self.socket = None

        self.connected = False


    def connection_lost(self):
        print ('Connection lost')
        self.close()
        self.fail_reason = 'closed'
        raise Exception('Lost connection')


    def connection_error(self, err, msg):
        print ('Connection Error: %d: %s' % (err, msg))
        self.close()
        if err == errno.ECONNREFUSED: self.fail_reason = 'refused'
        elif err in [errno.ETIMEDOUT, errno.ENETDOWN, errno.ENETUNREACH]:
            self.fail_reason = 'connect'
        else: self.fail_reason = 'error'


    def read_some(self):
        bytesRead = 0
        try:
            while True:
                buffer = self.socket.recv(10 * 1024 * 1024)
                if len(buffer):
                    #if debug: print 'BUFFER:', buffer
                    self.readBuf += buffer
                    bytesRead += len(buffer)
                else:
                    if bytesRead: return bytesRead
                    self.connection_lost()
                    return 0

        except socket.error as err:
            # Error codes for nothing to read
            if err.errno not in [errno.EAGAIN, errno.EWOULDBLOCK, WSAEWOULDBLOCK]:
                if bytesRead: return bytesRead
                self.connection_error(err, err.strerror)
                raise

        return bytesRead


    def write_some(self):
        if len(self.writeBuf) == 0: return 0

        bytesWritten = 0
        try:
            while True:
                count = self.socket.send(self.writeBuf)
                if count:
                    self.writeBuf = self.writeBuf[count:]
                    bytesWritten += count
                else:
                    if bytesWritten: return bytesWritten
                    self.connection_lost()
                    return 0

        except socket.error as err:
            # Error codes for write buffer full
            if err.errno not in [errno.EAGAIN, errno.EWOULDBLOCK, WSAEWOULDBLOCK]:
                if bytesWritten: return bytesWritten
                self.connection_error(err, msg)
                raise

        return bytesWritten


    def queue_command(self, command):
        if debug: print ('command: ' + command)
        self.writeBuf += command + '\n'


    def parse_message(self, version, type, data):
        try:
            msg = eval(data, {}, {})
            #if debug: print 'MSG:', type, msg
            self.messages.append((version, type, msg))
            self.last_message = time.time()
        except Exception as e:
            print ('ERROR parsing PyON message: %s: %s'
                   % (str(e), data.encode('string_escape')))


    def parse(self):
        start = self.readBuf.find('\nPyON ')
        if start != -1:
            eol = self.readBuf.find('\n', start + 1)
            if eol != -1:
                line = self.readBuf[start + 1: eol]
                tokens = line.split(None, 2)

                if len(tokens) < 3:
                    self.readBuf = self.readBuf[eol:]
                    raise Exception('Invalid PyON line: ' + line.encode('string_escape'))

                version = int(tokens[1])
                type = tokens[2]

                end = self.readBuf.find('\n---\n', start)
                if end != -1:
                    data = self.readBuf[eol + 1: end]
                    self.parse_message(version, type, data)
                    self.readBuf = self.readBuf[end + 4:]
                    return True

        return False


    def update(self):
        try:
            try:
                if not self.is_connected():
                    if self.socket is None:
                        if self.last_connect + self.retry_rate < time.time():
                            self.open()

                    elif self.last_connect + 60 < time.time():
                        self.close() # Retry connect

                if not self.is_connected(): return

                self.write_some()
                if self.read_some():
                    while self.parse(): continue

            # Handle special case for OSX disconnect
            except socket.error as e:
                if sys.platform == 'darwin' and e.errno == errno.EPIPE:
                    self.fail_reason = 'refused'
                    self.close()

                else: raise

        except Exception as e:
            print ('ERROR on connection to %s:%d: %s' % (self.address, self.port, e))

        # Timeout connection
        if self.connected and self.last_message and \
                self.last_message + 10 < time.time():
            print ('Connection timed out')
            self.close()



if __name__ == '__main__':
    init = ['updates add 0 1 $options',
            'updates add 1 1 $queue-info',
            'updates add 2 1 $slot-info']
    conn = Connection(init_commands = init)

    while True:
        conn.update()

        for version, type, data in conn.messages:
            print ('PyON %d %s:\n' % (version, type), data)
        conn.messages = []

        time.sleep(0.1)
