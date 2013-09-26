# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software

"""
The Option/BaseConfig classes is taken from config.py from the yum project (http://yum.baseurl.org )

It is modified to work in Python 3

"""

import copy
from urllib.parse import urlparse
import glob
import re

def read_in_items_from_dot_dir(thisglob, line_as_list=True):
    """takes a glob of a dir (like /etc/foo.d/*.foo)
       returns a list of all the lines in all the files matching
       that glob, ignores comments and blank lines,
       optional paramater 'line_as_list tells whether to
       treat each line as a space or comma-separated list, defaults to True"""
    results = []
    for fname in glob.glob(thisglob):
        for line in open(fname):
            if re.match('\s*(#|$)', line):
                continue
            line = line.rstrip() # no more trailing \n's
            line = line.lstrip() # be nice
            if not line:
                continue
            if line_as_list:
                line = line.replace('\n', ' ')
                line = line.replace(',', ' ')
                results.extend(line.split())
                continue
            results.append(line)
    return results


class Option(object):
    """
    This class handles a single Yum configuration file option. Create
    subclasses for each type of supported configuration option.
    Python descriptor foo (__get__ and __set__) is used to make option
    definition easy and concise.
    """

    def __init__(self, default=None, parse_default=False):
        self._setattrname()
        self.inherit = False
        if parse_default:
            default = self.parse(default)
        self.default = default

    def _setattrname(self):
        """Calculate the internal attribute name used to store option state in
        configuration instances.
        """
        self._attrname = '__opt%d' % id(self)

    def __get__(self, obj, objtype):
        """Called when the option is read (via the descriptor protocol). 

        :param obj: The configuration instance to modify.
        :param objtype: The type of the config instance (not used).
        :return: The parsed option value or the default value if the value
           wasn't set in the configuration file.
        """
        # xemacs highlighting hack: '
        if obj is None:
            return self

        return getattr(obj, self._attrname, None)

    def __set__(self, obj, value):
        """Called when the option is set (via the descriptor protocol). 

        :param obj: The configuration instance to modify.
        :param value: The value to set the option to.
        """
        # Only try to parse if it's a string
        if isinstance(value, str):
            try:
                value = self.parse(value)
            except ValueError as e:
                # Add the field name onto the error
                raise ValueError('Error parsing "%s = %r": %s' % (self._optname,
                                                                 value, str(e)))
        setattr(obj, self._attrname, value)

    def setup(self, obj, name):
        """Initialise the option for a config instance. 
        This must be called before the option can be set or retrieved. 

        :param obj: :class:`BaseConfig` (or subclass) instance.
        :param name: Name of the option.
        """
        self._optname = name
        setattr(obj, self._attrname, copy.copy(self.default))

    def clone(self):
        """Return a safe copy of this :class:`Option` instance.

        :return: a safe copy of this :class:`Option` instance
        """
        new = copy.copy(self)
        new._setattrname()
        return new

    def parse(self, s):
        """Parse the string value to the :class:`Option`'s native value.

        :param s: raw string value to parse
        :return: validated native value
        :raise: ValueError if there was a problem parsing the string.
           Subclasses should override this
        """
        return s

    def tostring(self, value):
        """Convert the :class:`Option`'s native value to a string value.  This
        does the opposite of the :func:`parse` method above.
        Subclasses should override this.

        :param value: native option value
        :return: string representation of input
        """
        return str(value)

def Inherit(option_obj):
    """Clone an :class:`Option` instance for the purposes of inheritance. The returned
    instance has all the same properties as the input :class:`Option` and shares items
    such as the default value. Use this to avoid redefinition of reused
    options.

    :param option_obj: :class:`Option` instance to inherit
    :return: New :class:`Option` instance inherited from the input
    """
    new_option = option_obj.clone()
    new_option.inherit = True
    return new_option

class ListOption(Option):
    """An option containing a list of strings."""

    def __init__(self, default=None, parse_default=False):
        if default is None:
            default = []
        super(ListOption, self).__init__(default, parse_default)

    def parse(self, s):
        """Convert a string from the config file to a workable list, parses
        globdir: paths as foo.d-style dirs.

        :param s: The string to be converted to a list. Commas and
           whitespace are used as separators for the list
        :return: *s* converted to a list
        """
        # we need to allow for the '\n[whitespace]' continuation - easier
        # to sub the \n with a space and then read the lines
        s = s.replace('\n', ' ')
        s = s.replace(',', ' ')
        results = []
        for item in s.split():
            if item.startswith('glob:'):
                thisglob = item.replace('glob:', '')
                results.extend(read_in_items_from_dot_dir(thisglob))
                continue
            results.append(item)

        return results

    def tostring(self, value):
        """Convert a list of to a string value.  This does the
        opposite of the :func:`parse` method above.

        :param value: a list of values
        :return: string representation of input
        """
        return '\n '.join(value)

class UrlOption(Option):
    """This option handles lists of URLs with validation of the URL
    scheme.
    """

    def __init__(self, default=None, schemes=('http', 'ftp', 'file', 'https'), 
            allow_none=False):
        super(UrlOption, self).__init__(default)
        self.schemes = schemes
        self.allow_none = allow_none

    def parse(self, url):
        """Parse a url to make sure that it is valid, and in a scheme
        that can be used.

        :param url: a string containing the url to parse
        :return: *url* if it is valid
        :raises: :class:`ValueError` if there is an error parsing the url
        """
        url = url.strip()

        # Handle the "_none_" special case
        if url.lower() == '_none_':
            if self.allow_none:
                return None
            else:
                raise ValueError('"_none_" is not a valid value')

        # Check that scheme is valid
        (s,b,p,q,f,o) = urlparse(url)
        if s not in self.schemes:
            raise ValueError('URL must be %s not "%s"' % (self._schemelist(), s))

        return url

    def _schemelist(self):
        '''Return a user friendly list of the allowed schemes
        '''
        if len(self.schemes) < 1:
            return 'empty'
        elif len(self.schemes) == 1:
            return self.schemes[0]
        else:
            return '%s or %s' % (', '.join(self.schemes[:-1]), self.schemes[-1])

class IntOption(Option):
    """An option representing an integer value."""

    def __init__(self, default=None, range_min=None, range_max=None):
        super(IntOption, self).__init__(default)
        self._range_min = range_min
        self._range_max = range_max
        
    def parse(self, s):
        """Parse a string containing an integer.

        :param s: the string to parse
        :return: the integer in *s*
        :raises: :class:`ValueError` if there is an error parsing the
           integer
        """
        try:
            val = int(s)
        except (ValueError, TypeError) as e:
            raise ValueError('invalid integer value')
        if self._range_max is not None and val > self._range_max:
            raise ValueError('out of range integer value')
        if self._range_min is not None and val < self._range_min:
            raise ValueError('out of range integer value')
        return val

class PositiveIntOption(IntOption):
    """An option representing a positive integer value, where 0 can
    have a special representation.
    """
    def __init__(self, default=None, range_min=0, range_max=None,
                 names_of_0=None):
        super(PositiveIntOption, self).__init__(default, range_min, range_max)
        self._names0 = names_of_0

    def parse(self, s):
        """Parse a string containing a positive integer, where 0 can
           have a special representation.

        :param s: the string to parse
        :return: the integer in *s*
        :raises: :class:`ValueError` if there is an error parsing the
           integer
        """
        if s in self._names0:
            return 0
        return super(PositiveIntOption, self).parse(s)

class SecondsOption(Option):
    """An option representing an integer value of seconds, or a human
    readable variation specifying days, hours, minutes or seconds
    until something happens. Works like :class:`BytesOption`.  Note
    that due to historical president -1 means "never", so this accepts
    that and allows the word never, too.

    Valid inputs: 100, 1.5m, 90s, 1.2d, 1d, 0xF, 0.1, -1, never.
    Invalid inputs: -10, -0.1, 45.6Z, 1d6h, 1day, 1y.

    Return value will always be an integer
    """
    MULTS = {'d': 60 * 60 * 24, 'h' : 60 * 60, 'm' : 60, 's': 1}

    def parse(self, s):
        """Parse a string containing an integer value of seconds, or a human
        readable variation specifying days, hours, minutes or seconds
        until something happens. Works like :class:`BytesOption`.  Note
        that due to historical president -1 means "never", so this accepts
        that and allows the word never, too.
    
        Valid inputs: 100, 1.5m, 90s, 1.2d, 1d, 0xF, 0.1, -1, never.
        Invalid inputs: -10, -0.1, 45.6Z, 1d6h, 1day, 1y.
    
        :param s: the string to parse
        :return: an integer representing the number of seconds
           specified by *s*
        :raises: :class:`ValueError` if there is an error parsing the string
        """
        if len(s) < 1:
            raise ValueError("no value specified")

        if s == "-1" or s == "never": # Special cache timeout, meaning never
            return -1
        if s[-1].isalpha():
            n = s[:-1]
            unit = s[-1].lower()
            mult = self.MULTS.get(unit, None)
            if not mult:
                raise ValueError("unknown unit '%s'" % unit)
        else:
            n = s
            mult = 1

        try:
            n = float(n)
        except (ValueError, TypeError) as e:
            raise ValueError('invalid value')

        if n < 0:
            raise ValueError("seconds value may not be negative")

        return int(n * mult)

class BoolOption(Option):
    """An option representing a boolean value.  The value can be one
    of 0, 1, yes, no, true, or false.
    """

    def parse(self, s):
        """Parse a string containing a boolean value.  1, yes, and
        true will evaluate to True; and 0, no, and false will evaluate
        to False.  Case is ignored.
        
        :param s: the string containing the boolean value
        :return: the boolean value contained in *s*
        :raises: :class:`ValueError` if there is an error in parsing
           the boolean value
        """
        s = s.lower()
        if s in ('0', 'no', 'false'):
            return False
        elif s in ('1', 'yes', 'true'):
            return True
        else:
            raise ValueError('invalid boolean value')

    def tostring(self, value):
        """Convert a boolean value to a string value.  This does the
        opposite of the :func:`parse` method above.
        
        :param value: the boolean value to convert
        :return: a string representation of *value*
        """
        if value:
            return "1"
        else:
            return "0"

class FloatOption(Option):
    """An option representing a numeric float value."""

    def parse(self, s):
        """Parse a string containing a numeric float value.

        :param s: a string containing a numeric float value to parse
        :return: the numeric float value contained in *s*
        :raises: :class:`ValueError` if there is an error parsing
           float value
        """
        try:
            return float(s.strip())
        except (ValueError, TypeError):
            raise ValueError('invalid float value')

class SelectionOption(Option):
    """Handles string values where only specific values are
    allowed.
    """
    def __init__(self, default=None, allowed=(), mapper={}):
        super(SelectionOption, self).__init__(default)
        self._allowed = allowed
        self._mapper  = mapper
        
    def parse(self, s):
        """Parse a string for specific values.

        :param s: the string to parse
        :return: *s* if it contains a valid value
        :raises: :class:`ValueError` if there is an error parsing the values
        """
        if s in self._mapper:
            s = self._mapper[s]
        if s not in self._allowed:
            raise ValueError('"%s" is not an allowed value' % s)
        return s

class CaselessSelectionOption(SelectionOption):
    """Mainly for compatibility with :class:`BoolOption`, works like
    :class:`SelectionOption` but lowers input case.
    """
    def parse(self, s):
        """Parse a string for specific values.

        :param s: the string to parse
        :return: *s* if it contains a valid value
        :raises: :class:`ValueError` if there is an error parsing the values
        """
        return super(CaselessSelectionOption, self).parse(s.lower())

class BytesOption(Option):
    """An option representing a value in bytes. The value may be given
    in bytes, kilobytes, megabytes, or gigabytes.
    """
    # Multipliers for unit symbols
    MULTS = {
        'k': 1024,
        'm': 1024*1024,
        'g': 1024*1024*1024,
    }

    def parse(self, s):
        """Parse a friendly bandwidth option to bytes.  The input
        should be a string containing a (possibly floating point)
        number followed by an optional single character unit. Valid
        units are 'k', 'M', 'G'. Case is ignored. The convention that
        1k = 1024 bytes is used.
       
        Valid inputs: 100, 123M, 45.6k, 12.4G, 100K, 786.3, 0.
        Invalid inputs: -10, -0.1, 45.6L, 123Mb.

        :param s: the string to parse
        :return: the number of bytes represented by *s*
        :raises: :class:`ValueError` if the option can't be parsed
        """
        if len(s) < 1:
            raise ValueError("no value specified")

        if s[-1].isalpha():
            n = s[:-1]
            unit = s[-1].lower()
            mult = self.MULTS.get(unit, None)
            if not mult:
                raise ValueError("unknown unit '%s'" % unit)
        else:
            n = s
            mult = 1
             
        try:
            n = float(n)
        except ValueError:
            raise ValueError("couldn't convert '%s' to number" % n)

        if n < 0:
            raise ValueError("bytes value may not be negative")

        return int(n * mult)

class ThrottleOption(BytesOption):
    """An option representing a bandwidth throttle value. See
    :func:`parse` for acceptable input values.
    """

    def parse(self, s):
        """Get a throttle option. Input may either be a percentage or
        a "friendly bandwidth value" as accepted by the
        :class:`BytesOption`.

        Valid inputs: 100, 50%, 80.5%, 123M, 45.6k, 12.4G, 100K, 786.0, 0.
        Invalid inputs: 100.1%, -4%, -500.

        :param s: the string to parse
        :return: the bandwidth represented by *s*. The return value
           will be an int if a bandwidth value was specified, and a
           float if a percentage was given
        :raises: :class:`ValueError` if input can't be parsed
        """
        if len(s) < 1:
            raise ValueError("no value specified")

        if s[-1] == '%':
            n = s[:-1]
            try:
                n = float(n)
            except ValueError:
                raise ValueError("couldn't convert '%s' to number" % n)
            if n < 0 or n > 100:
                raise ValueError("percentage is out of range")
            return n / 100.0
        else:
            return BytesOption.parse(self, s)

class BaseConfig(object):
    """Base class for storing configuration definitions. Subclass when
    creating your own definitions.
    """

    def __init__(self):
        self._section = None

        for name in self.iterkeys():
            option = self.optionobj(name)
            option.setup(self, name)

    def __str__(self):
        out = []
        out.append('[%s]' % self._section)
        for name, value in self.iteritems():
            out.append('%s: %r' % (name, value))
        return '\n'.join(out)

    def populate(self, parser, section, parent=None):
        """Set option values from an INI file section.

        :param parser: :class:`ConfigParser` instance (or subclass)
        :param section: INI file section to read use
        :param parent: Optional parent :class:`BaseConfig` (or
            subclass) instance to use when doing option value
            inheritance
        """
        self.cfg = parser
        self._section = section

        if parser.has_section(section):
            opts = set(parser.options(section))
        else:
            opts = set()
        for name in self.iterkeys():
            option = self.optionobj(name)
            value = None
            if name in opts:
                value = parser.get(section, name)
            else:
                # No matching option in this section, try inheriting
                if parent and option.inherit:
                    value = getattr(parent, name)
               
            if value is not None:
                setattr(self, name, value)

    def optionobj(cls, name, exceptions=True):
        """Return the :class:`Option` instance for the given name.

        :param cls: the class to return the :class:`Option` instance from
        :param name: the name of the :class:`Option` instance to return
        :param exceptions: defines what action to take if the
           specified :class:`Option` instance does not exist. If *exceptions* is
           True, a :class:`KeyError` will be raised. If *exceptions*
           is False, None will be returned
        :return: the :class:`Option` instance specified by *name*, or None if
           it does not exist and *exceptions* is False
        :raises: :class:`KeyError` if the specified :class:`Option` does not
           exist, and *exceptions* is True
        """
        obj = getattr(cls, name, None)
        if isinstance(obj, Option):
            return obj
        elif exceptions:
            raise KeyError
        else:
            return None
    optionobj = classmethod(optionobj)

    def isoption(cls, name):
        """Return True if the given name refers to a defined option.

        :param cls: the class to find the option in
        :param name: the name of the option to search for
        :return: whether *name* specifies a defined option
        """
        return cls.optionobj(name, exceptions=False) is not None
    isoption = classmethod(isoption)

    def iterkeys(self):
        """Yield the names of all defined options in the instance."""

        for name in dir(self):
            if self.isoption(name):
                yield name

    def iteritems(self):
        """Yield (name, value) pairs for every option in the
        instance. The value returned is the parsed, validated option
        value.
        """
        # Use dir() so that we see inherited options too
        for name in self.iterkeys():
            yield (name, getattr(self, name))

    def write(self, fileobj, section=None, always=()):
        """Write out the configuration to a file-like object.

        :param fileobj: File-like object to write to
        :param section: Section name to use. If not specified, the section name
            used during parsing will be used
        :param always: A sequence of option names to always write out.
            Options not listed here will only be written out if they are at
            non-default values. Set to None to dump out all options
        """
        # Write section heading
        if section is None:
            if self._section is None:
                raise ValueError("not populated, don't know section")
            section = self._section

        # Updated the ConfigParser with the changed values    
        cfgOptions = self.cfg.options(section)
        for name,value in self.iteritems():
            option = self.optionobj(name)
            if always is None or name in always or option.default != value or name in cfgOptions :
                self.cfg.set(section,name, option.tostring(value))
        # write the updated ConfigParser to the fileobj.
        self.cfg.write(fileobj)

