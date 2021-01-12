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

from fah.db import Column, Table

import sqlite3


class Database:
    tables = [
        Table('config',
              [
                Column('name', 'Text', 'NOT NULL'),
                Column('value', 'Text', 'NOT NULL'),
                ],
              'PRIMARY KEY (name)'),

        Table('clients',
              [
                Column('name', 'Text', 'NOT NULL'),
                Column('address', 'Text', 'NOT NULL'),
                Column('port', 'Integer', 'NOT NULL'),
                Column('password', 'Text', 'NOT NULL'),
                ],
              'PRIMARY KEY (name)'),
        ]


    def __init__(self, filename):
        self.filename = filename
        self.conn = sqlite3.connect(filename)
        self.conn.row_factory = sqlite3.Row
        self.queue = {}


    def get_table(self, name):
        for table in self.tables:
            if table.name == name: return table

        raise Exception('Table "%s" not found' % name)


    def get_version(self):
        return 6


    def get_current_version(self):
        return int(self.execute_one('PRAGMA user_version')[0])


    def set_current_version(self, version):
        self.write('PRAGMA user_version=%d' % version, True)


    def set(self, name, value, commit = True, queue = False):
        if queue: self.queue[name] = value
        else:
            self.insert('config', name = name, value = value)
            if commit: self.commit()


    def clear(self, name, commit = True):
        self.delete('config', name = name)
        if commit: self.commit()


    def get(self, name):
        c = self.get_table('config').select(self, 'value', name = name)
        result = c.fetchone()
        c.close()
        if result: return result[0]


    def has(self, name):
        return self.get(name) is not None

    def default(self, name, default, commit = True):
        if not self.has(name): self.set(name, default, commit)


    def flush_queued(self):
        if len(self.queue) == 0: return

        for name, value in list(self.queue.items()):
            self.set(name, value, commit = False)

        self.commit()
        self.queue.clear()


    def execute(self, sql):
        #print 'SQL:', sql
        c = self.conn.cursor()
        c.execute(sql)
        return c


    def execute_one(self, sql):
        c = self.execute(sql)
        result = c.fetchone()
        c.close()
        return result


    def write(self, sql, commit = False):
        self.execute(sql).close()
        if commit: self.commit()


    def commit(self):
        self.conn.commit()


    def rollback(self):
        self.conn.rollback()


    def insert(self, table, **kwargs):
        self.get_table(table).insert(self, **kwargs)


    def delete(self, table, **kwargs):
        self.get_table(table).delete(self, **kwargs)


    def select(self, table, cols = None, **kwargs):
        return self.get_table(table).select(self, cols, **kwargs)


    def create(self):
        for table in self.tables:
            table.create(self)
        self.commit()


    def validate(self):
        current = self.get_current_version()
        if self.get_version() < current:
            raise Exception('Configuration database "%s" version %d is newer than is supported %d'
                            % (self.filename, current, self.get_version()))

        elif self.get_version() != current:
            # Create or upgrade DB

            if current == 0: self.create()
            else:
                if current <= 2:
                    # Just drop and recreate the clients table
                    self.execute('DROP TABLE IF EXISTS clients')
                    for table in self.tables:
                        if table.name == 'clients': table.create(self)

                if current <= 5:
                    self.execute('DROP TABLE IF EXISTS projects')

            self.set_current_version(self.get_version())
            self.commit()
