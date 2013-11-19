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


from utils import deltaCalc

from django import test

from mantis_iodef_importer.management.commands.mantis_iodef_import import Command

from custom_test_runner import CustomSettingsTestCase

import pprint

pp = pprint.PrettyPrinter(indent=22)


class XML_Import_Tests(CustomSettingsTestCase):

    new_settings = dict(
        INSTALLED_APPS=(
           'dingos',
        )
    )

    def setUp(self):
        self.command = Command()
 
    def common_import_delta(self, xml_file):
        """ Returns the resulting list of elements parsing a given XML file in IODEF format """

        @deltaCalc
        def t_import(*args,**kwargs):
            return self.command.handle(*args,**kwargs)


        (delta,result) = t_import(xml_file,
                                  identifier_ns_uri=None)
        #pp.pprint(delta)
        return delta

    def test_botnet_example_import(self):
        expected = [ ('DataTypeNameSpace', 2),
                     ('Fact', 34),
                     ('FactDataType', 1),
                     ('FactTerm', 28),
                     ('FactTerm2Type', 28),
                     ('FactValue', 34),
                     ('Identifier', 1),
                     ('IdentifierNameSpace', 1),
                     ('InfoObject', 1),
                     ('InfoObject2Fact', 40),
                     ('InfoObjectFamily', 1),
                     ('InfoObjectType', 1),
                     ('NodeID', 40),
                     ('Revision', 1)
                    ]
        self.assertEqual( expected, self.common_import_delta('tests/mocks/botnet_iodef.xml') )

    def test_scan_example(self):
        expected =  [ ('DataTypeNameSpace', 2),
                      ('Fact', 30),
                      ('FactDataType', 1),
                      ('FactTerm', 24),
                      ('FactTerm2Type', 24),
                      ('FactValue', 33),
                      ('Identifier', 1),
                      ('IdentifierNameSpace', 1),
                      ('InfoObject', 1),
                      ('InfoObject2Fact', 36),
                      ('InfoObjectFamily', 1),
                      ('InfoObjectType', 1),
                      ('NodeID', 36),
                      ('Revision', 1)
                    ]
        self.assertEqual( expected, self.common_import_delta('tests/mocks/scan_iodef.xml') )

    def test_worm_example(self):
        expected =  [ ('DataTypeNameSpace', 2),
                      ('Fact', 34),
                      ('FactDataType', 3),
                      ('FactTerm', 29),
                      ('FactTerm2Type', 29),
                      ('FactValue', 33),
                      ('Identifier', 1),
                      ('IdentifierNameSpace', 1),
                      ('InfoObject', 1),
                      ('InfoObject2Fact', 34),
                      ('InfoObjectFamily', 1),
                      ('InfoObjectType', 1),
                      ('NodeID', 34),
                      ('Revision', 1)
                    ]
        self.assertEqual( expected, self.common_import_delta('tests/mocks/worm_iodef.xml') )
