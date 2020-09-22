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

import re
import json
import sys


NUMBER_RE = re.compile(r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
                       (re.VERBOSE | re.MULTILINE | re.DOTALL))
FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL
STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
  '"': u'"', '\\': u'\\', '/': u'/',
  'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"


def linecol(doc, pos):
  lineno = doc.count('\n', 0, pos) + 1
  if lineno == 1:
    colno = pos + 1
  else:
    colno = pos - doc.rindex('\n', 0, pos)
  return lineno, colno


def errmsg(msg, doc, pos, end=None):
  # Note that this function is called from _json
  lineno, colno = linecol(doc, pos)
  if end is None:
    fmt = '{0}: line {1} column {2} (char {3})'
    return fmt.format(msg, lineno, colno, pos)

  endlineno, endcolno = linecol(doc, end)
  fmt = '{0}: line {1} column {2} - line {3} column {4} (char {5} - {6})'
  return fmt.format(msg, lineno, colno, endlineno, endcolno, pos, end)


def _decode_uXXXX(s, pos):
  esc = s[pos + 1:pos + 5]

  if len(esc) == 4 and esc[1] not in 'xX':
    try:
      return int(esc, 16)
    except ValueError: pass

  msg = "Invalid \\uXXXX escape"
  raise ValueError(errmsg(msg, s, pos))


def pyon_scanstring(s, end, encoding = None, strict = True,
                    _b = BACKSLASH, _m = STRINGCHUNK.match):
  """Scan the string s for a JSON string. End is the index of the
  character in s after the quote that started the JSON string.
  Unescapes all valid JSON string escape sequences and raises ValueError
  on attempt to decode an invalid string. If strict is False then literal
  control characters are allowed in the string.
  Returns a tuple of the decoded string and the index of the character in s
  after the end quote."""
  if encoding is None: encoding = DEFAULT_ENCODING
  chunks = []
  _append = chunks.append
  begin = end - 1

  while True:
    chunk = _m(s, end)
    if chunk is None:
      raise ValueError(
        errmsg("Unterminated string starting at", s, begin))

    end = chunk.end()
    content, terminator = chunk.groups()

    # Content is contains zero or more unescaped string characters
    if content:
      if not isinstance(content, unicode):
        content = unicode(content, encoding)
      _append(content)

    # Terminator is the end of string, a literal control character,
    # or a backslash denoting that an escape sequence follows
    if terminator == '"': break
    elif terminator != '\\':
      if strict:
        msg = "Invalid control character {0!r} at".format(terminator)
        raise ValueError(errmsg(msg, s, end))
      else:
        _append(terminator)
        continue

    try:
      esc = s[end]
    except IndexError:
      raise ValueError(errmsg("Unterminated string starting at", s, begin))

    # If not a unicode escape sequence, must be in the lookup table
    if esc != 'u' and esc != 'x':
      try:
        char = _b[esc]
      except KeyError:
        msg = "Invalid \\escape: " + repr(esc)
        raise ValueError(errmsg(msg, s, end))
      end += 1

    elif esc == 'x':
      # Hex escape sequence
      try:
        code = s[end + 1: end + 3]
        char = code.decode('hex')
      except:
        raise ValueError(errmsg('Invalid \\escape: ' + repr(code), s, end))

      end += 3

    else:
      # Unicode escape sequence
      uni = _decode_uXXXX(s, end)
      end += 5
      # Check for surrogate pair on UCS-4 systems
      if sys.maxunicode > 65535 and \
         0xd800 <= uni <= 0xdbff and s[end:end + 2] == '\\u':
        uni2 = _decode_uXXXX(s, end + 1)
        if 0xdc00 <= uni2 <= 0xdfff:
          uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
          end += 6
      char = unichr(uni)

    # Append the unescaped character
    _append(char)

  return u''.join(chunks), end



def make_pyon_scanner(context):
  parse_object = context.parse_object
  parse_array = context.parse_array
  parse_string = context.parse_string
  match_number = NUMBER_RE.match
  strict = context.strict
  parse_float = context.parse_float
  parse_int = context.parse_int
  parse_constant = context.parse_constant
  object_hook = context.object_hook
  object_pairs_hook = context.object_pairs_hook


  def scan_once(string, idx):
    try:
        nextchar = string[idx]
    except IndexError:
      raise StopIteration(idx)

    if nextchar == '"': return parse_string(string, idx + 1, 'utf-8', strict)
    elif nextchar == '{':
      return parse_object((string, idx + 1), 'utf-8', strict, scan_once,
                          object_hook, object_pairs_hook)
    elif nextchar == '[':
      return parse_array((string, idx + 1), scan_once)
    elif nextchar == 'N' and string[idx:idx + 4] == 'None':
      return None, idx + 4
    elif nextchar == 'T' and string[idx:idx + 4] == 'True':
      return True, idx + 4
    elif nextchar == 'F' and string[idx:idx + 5] == 'False':
      return False, idx + 5

    m = match_number(string, idx)
    if m is not None:
      integer, frac, exp = m.groups()
      if frac or exp:
        res = parse_float(integer + (frac or '') + (exp or ''))
      else: res = parse_int(integer)

      return res, m.end()

    elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
      return parse_constant('NaN'), idx + 3

    elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
      return parse_constant('Infinity'), idx + 8

    elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
      return parse_constant('-Infinity'), idx + 9

    else: raise StopIteration(idx)


  return scan_once


class PYONDecoder(json.JSONDecoder):
  def __init__(self, *args, **kwargs):
    json.JSONDecoder.__init__(self, *args, **kwargs)
    self.parse_string = pyon_scanstring
    self.scan_once = make_pyon_scanner(self)
