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

class Column:
    def __init__(self, name, dbType, constraits, auto = False):
        self.name = name
        self.dbType = dbType.lower()
        self.constraints = constraits
        self.auto = auto


    def get_name(self): return self.name
    def is_auto(self): return self.auto


    def get_db_value(self, value):
        if self.dbType == 'text': return "'%s'" % str(value).replace("'", "''")
        if self.dbType == 'integer': return '%d' % value
        if self.dbType == 'real': return '%f' % value
        if self.dbType == 'boolean':
            if value: return '1'
            else: return '0'


    def get_sql(self):
        return '"%s" %s %s' % (self.name, self.dbType, self.constraints)


    def __hash__(self): return self.name.__hash__()
    def __cmp__(self, other): return self.name.__cmp__(other.name)
    def __str__(self): return self.name
