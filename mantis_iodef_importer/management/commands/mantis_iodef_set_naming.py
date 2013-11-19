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

import sys

import pprint

from django.core.management.base import BaseCommand, CommandError
from optparse import make_option

from dingos.models import InfoObjectType, InfoObjectNaming

from dingos.management.commands.dingos_manage_naming_schemas import Command as ManageCommand


schema_list = [
    [
        "Incident",
        "iodef",
        "urn:ietf:params:xml:ns:iodef",
        [
            "[Description] ([@purpose])",
            "[Description]"
        ]
    ]
]

manage_command = ManageCommand()

pp = pprint.PrettyPrinter(indent=2)

class Command(ManageCommand):
    """

    """
    args = ''
    help = 'Set standard naming schema for InfoObjects from IODEF import. Run this once before importing IODEF files.'

    option_list = BaseCommand.option_list

    def __init__(self, *args, **kwargs):
        kwargs['schemas'] = schema_list
        super(Command,self).__init__(*args,**kwargs)


    def handle(self, *args, **options):
        options['input_list'] = self.schemas
        #manage_command.handle(*args,**options)
        super(Command,self).handle(*args,**options)

