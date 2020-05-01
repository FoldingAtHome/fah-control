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

from fah.db import Column


class Table:
    def __init__(self, name, cols, constraints = ''):
        self.name = name
        self.cols = cols
        self.constraints = constraints


    def where(self, **kwargs):
        if len(kwargs) == 0: return ''
        sql = 'WHERE '

        if len(kwargs) == 1 and 'where' in kwargs:
            sql += kwargs['where']

        else:
            sql +=\
                ' AND '.join(['"%s"=\'%s\'' % i for i in list(kwargs.items())])

        return sql


    def create(self, db):
        sql = 'CREATE TABLE IF NOT EXISTS "%s" (%s' % (
            self.name, ','.join(map(Column.get_sql, self.cols)))

        if self.constraints: sql += ',%s' % self.constraints
        sql += ')'

        db.execute(sql).close()


    def insert(self, db, **kwargs):
        cols = [col for col in self.cols if col.name in kwargs]

        # Error checking
        if len(cols) != len(kwargs):
            col_names = set(map(Column.get_name, cols))
            missing = [kw for kw in list(kwargs.keys()) if kw not in col_names]
            raise Exception('Table %s does not have column(s) %s'
                            % (self.name, ', '.join(missing)))

        sql = 'REPLACE INTO "%s" ("%s") VALUES (%s)' % (
            self.name, '","'.join(map(Column.get_name, cols)),
            ','.join([col.get_db_value(kwargs[col.name]) for col in cols]))

        db.execute(sql).close()

    def select(self, db, cols = None, **kwargs):
        if cols is None:
            cols = '"' + '","'.join(map(str, self.cols)) + '"'

        sql = 'SELECT %s FROM %s' % (cols, self.name)
        if 'orderby' in kwargs:
            sql += ' ORDER BY ' + kwargs['orderby']
            del kwargs['orderby']

        sql += ' ' + self.where(**kwargs)

        return db.execute(sql)


    def delete(self, db, **kwargs):
        sql = 'DELETE FROM %s %s' % (self.name, self.where(**kwargs))
        db.execute(sql).close()


    def drop(self, db):
        db.execute('DROP TABLE IF EXISTS ' + self.name).close()
