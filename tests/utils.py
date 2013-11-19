# Copyright (c) Siemens AG, 2013
#
# This file is part of MANTIS.  MANTIS is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either version 2
# of the License, or(at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#


import pprint

pp = pprint.PrettyPrinter(indent=2)

from dingos.models import dingos_class_map


def object_counter():
    """
    Returns a tuple that contains counts of how many objects of each model
    defined in dingos.models are in the database.
    """
    class_names = dingos_class_map.keys()
    class_names.sort()
    result = []
    for class_name in class_names:
        result.append((class_name, len(dingos_class_map[class_name].objects.all())))
    return result


def object_count_delta(count1, count2):
    """
    Calculates the difference between to object counts.
    """
    result = []
    for i in range(0, len(count1)):
        if (count2[i][1] - count1[i][1]) != 0:
            result.append((count1[i][0], count2[i][1] - count1[i][1]))
    return result


def deltaCalc(func):
    """
    This is a decorator that wraps functions for test purposes with
    a count of objects in the database. It returns the
    delta of the objects for each model class along with
    the result of the tested function.
    """

    def inner(*args, **kwargs):
        count_pre = object_counter()
        #print "PRE"
        #pp.pprint(count_pre)
        result = func(*args, **kwargs)
        count_post = object_counter()
        #print "POST"
        #pp.pprint(count_post)
        delta = object_count_delta(count_pre, count_post)
        #print "DELTA"
        #pp.pprint(delta)
        return (delta, result)

    return inner



