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


import logging

import re

from django.utils import timezone

from django.utils.dateparse import parse_datetime

from dingos import *

from dingos.core.datastructures import DingoObjDict

from dingos.core.utilities import search_by_re_list, set_dict

from dingos.core.xml_utils import extract_attributes

from mantis_core.import_handling import MantisImporter

from mantis_core.models import FactDataType

from mantis_core.models import Identifier

logger = logging.getLogger(__name__)

class iodef_Import:


    def __init__(self, *args, **kwargs):

        self.toplevel_attrs = {}

        self.namespace_dict = {None:DINGOS_NAMESPACE_URI}

        self.iobject_family_name = 'iodef'
        self.iobject_family_revision_name = ''


        self.create_timestamp = timezone.now()
        self.identifier_ns_uri = DINGOS_DEFAULT_ID_NAMESPACE_URI

    #
    # First of all, we define functions for the hooks provided to us
    # by the DINGO xml-import.
    #



    def id_and_revision_extractor(self,xml_elt):
        """
        Function for generating a unique identifier for extracted embedded content;
        to be used for DINGO's xml-import hook 'embedded_id_gen'.

        This function is called

        - for the top-level node of the XML to be imported
        - for each node at which an embedded object is extracted from the XML
          (when this occurs is governed by the following function, the
          embedding_pred

        It must return an identifier and, where applicable, a revision and or timestamp.

        """

        result = { 'id': None, 'timestamp': None  }

        if not xml_elt.name == "Incident":
            return result


        child = xml_elt.children
        while child:
            attributes = extract_attributes(child,prefix_key_char='')

            if child.name == "IncidentID":
                result['id'] = '%s:%s' % (attributes.get('name'), child.content)

            elif child.name == "ReportTime":
                naive = parse_datetime(child.content)
                if not timezone.is_aware(naive):
                    aware = timezone.make_aware(naive,timezone.utc)
                else:
                    aware = naive
                result['timestamp'] = aware

            child = child.next
  
       
        return result


    def embedding_pred(self,parent, child, ns_mapping):
        """
        Predicate for recognizing inlined content in an XML; to
        be used for DINGO's xml-import hook 'embedded_predicate'.

        It returns either 
        - False (the child is not to be extracted)
        - True (the child is extracted but nothing can be inferred
          about what kind of object is extracted)
        - a string giving some indication about the object type
          (if nothing else is known: the name of the element)

        """
        
        values = extract_attributes(parent,prefix_key_char='@')

        # Incident - see RFC5070 page 12
        if child.name == 'Incident': # and values.get('@purpose') in [ 'traceback', 'migration', 'reporting', 'other', 'ext-value' ]:
	    return child.name
        return False


    def transformer(self,elt_name,contents):
        """
        This function is called for each DingoObjectDict
        that is created during the XML import process:
        it is given the element name and the DingObject Dict
        for the contents found under that element.
        
        For example, consider the following OpenIOC snippet::

              <IndicatorItem id="b9ef2559-cc59-4463-81d9-52800545e16e" condition="contains">
                   <Context document="FileItem" search="FileItem/PEInfo/Sections/Section/Name" type="mir"/>
                   <Content type="string">.stub</Content>
              </IndicatorItem>

        This is converted into a Dingo Object Dict of the form::

               'IndicatorItem' : { '@id': 'b9ef2559-cc59-4463-81d9-52800545e16e",
                                   '@condition' : "contains",
                                   'Context' : {'@document': 'FileItem',
                                                   ...
                                              },
                                   'Content' : {'@type' : 'string',
                                                '_value' : '.stub'
                                              }
                                 }

        For this, the tranformer is called with elt_name = 'IndicatorItem' and contents equal
        to the dictionary structure shown above. If you want to manipulate certain
        dictionary structures, the tranformer function is the place for it: it has
        to return a pair of ('new_element_name','new_content_dictionary').

        """
        return (elt_name,contents)


    # Next, we define functions for the hooks provided by the
    # 'from_dict' method of DINGO InfoObject Objects.
    #
    # These hook allow us to influence, how information contained
    # in a DingoObjDict is imported into the system.
    #
    # The hooking is carried out by defining a list
    # containing pairs of predicates (i.e., a function returning True or False)
    # and an associated hooking function. For each InfoObject2Fact object
    # (in the first case) resp. each attribute (in the second case),
    # the list is iterated by applying the predicate to input data.
    # If the predicate returns True, then the hooking function is applied
    # and may change the parameters for creation of fact.
    
    # What is usually at least required here is a 'reference handler' that
    # knows how to deal with references created by the import when extracting
    # an embedded object. Please have a look at the OpenIOC and STIX importers
    # to see how this works.



    def fact_handler_list(self):
        """
        The fact handler list consists of a pairs of predicate and handler function
        If the predicate returns 'True' for a fact to be added to an Information Object,
        the handler function is executed and may modify the parameters that will be passed
        to the function creating the fact.

        The signature of a predicate is as follows:

        - Inputs:
          - fact dictionary of the following form::

               { 'node_id': 'N001:L000:N000:A000',
                 'term': 'Hashes/Hash/Simple_Hash_Value',
                 'attribute': 'condition' / False,
                 'value': u'Equals'
               }
          - attr_info:
            A dictionary with mapping of XML attributes concerning the node in question
            (note that the keys do *not* have a leading '@' unless it is an internally
            generated attribute by Dingo.

        - Output: Based on these inputs, the predicate must return True or False. If True
          is returned, the associated handler function is run.

        The signature of a handler function is as follows:

        - Inputs:

          - info_object: the information object to which the fact is to be added
          - fact: the fact dictionary of the following form::
               { 'node_id': 'N001:L000:N000:A000',
                 'term': 'Hashes/Hash/Simple_Hash_Value',
                 'attribute': 'condition' / False,
                 'value': u'Equals'
               }
          - attr_info:
            A dictionary with mapping of XML attributes concerning the node in question
            (note that the keys do *not* have a leading '@' unless it is an internally
            generated attribute by Dingo.

          - add_fact_kargs:
            The arguments with which the fact will be generated after all handler functions
            have been called. The dictionary contains the following keys::

                'fact_dt_kind' : <FactDataType.NO_VOCAB/VOCAB_SINGLE/...>
                'fact_dt_namespace_name': <human-readable shortname for namespace uri>
                'fact_dt_namespace_uri': <namespace uri for datataype namespace>
                'fact_term_name' : <Fact Term such as 'Header/Subject/Address'>
                'fact_term_attribute': <Attribute key such as 'category' for fact terms describing an attribute>
                'values' : <list of FactValue objects that are the values of the fact to be generated>
                'node_id_name' : <node identifier such as 'N000:N000:A000'

        - Outputs:

          The handler function outputs either True or False: If False is returned,
          then the fact will *not* be generated. Please be aware that if you use this option,
          then there will be 'missing' numbers in the sequence of node ids.
          Thus, if you want to suppress the creation of facts for attributes,
          rather use the hooking function 'attr_ignore_predicate'

          As side effect, the function can make changes to the dictionary passed in parameter
          'add_fact_kargs' and thus change the fact that will be created.

        """

        return [ (lambda fact, attr_info: fact['term'].split('/')[-1] == "Portlist", self.iodef_portlist_fact_handler) ]

    def iodef_portlist_fact_handler(self, enrichment, fact, attr_info, add_fact_kargs):
        """
        Handler for dealing with 'Portlist' values.

        Comma-separated lists are allowed within the Portlist-node in IODEF.

        This handler is called for elements concerning a portlist-node
        such as the following example:

		<Service ip_protocol="6">
		    <Portlist>60524,60526,60527,60531</Portlist>
		</Service>
        """

        add_fact_kargs['values'] = fact['value'].split(',')
        return True


    def attr_ignore_predicate(self,fact_dict):
        """
        The attr_ignore predicate is called for each fact that would be generated
        for an XML attribute. It takes a fact dictionary of the following form
        as input::
               { 'node_id': 'N001:L000:N000:A000',
                 'term': 'Hashes/Hash/Simple_Hash_Value',
                 'attribute': 'condition',
                 'value': u'Equals'
               }

        If the predicate returns 'False, the fact is *not* created. Note that, nevertheless,
        during import, the information about this attribute is available to
        the attributed fact as part of the 'attr_dict' that is generated for the creation
        of each fact and passed to the handler functions called for the fact.

        """

        if '@' in fact_dict['attribute']:
            # We remove all attributes added by Dingo during import
            return True

        return False

    def datatype_extractor(self,iobject, fact, attr_info, namespace_mapping, add_fact_kargs):
        """

        The datatype extractor is called for each fact with the aim of determining the fact's datatype.
        The extractor function has the following signature:

        - Inputs:
          - info_object: the information object to which the fact is to be added
          - fact: the fact dictionary of the following form::
               { 'node_id': 'N001:L000:N000:A000',
                 'term': 'Hashes/Hash/Simple_Hash_Value',
                 'attribute': 'condition' / False,
                 'value': u'Equals'
               }
          - attr_info:
            A dictionary with mapping of XML attributes concerning the node in question
            (note that the keys do *not* have a leading '@' unless it is an internally
            generated attribute by Dingo.
          - namespace_mapping:
            A dictionary containing the namespace mapping extracted from the imported XML file.
          - add_fact_kargs:
            The arguments with which the fact will be generated after all handler functions
            have been called. The dictionary contains the following keys::

                'fact_dt_kind' : <FactDataType.NO_VOCAB/VOCAB_SINGLE/...>
                'fact_dt_namespace_name': <human-readable shortname for namespace uri>
                'fact_dt_namespace_uri': <namespace uri for datataype namespace>
                'fact_term_name' : <Fact Term such as 'Header/Subject/Address'>
                'fact_term_attribute': <Attribute key such as 'category' for fact terms describing an attribute>
                'values' : <list of FactValue objects that are the values of the fact to be generated>
                'node_id_name' : <node identifier such as 'N000:N000:A000'

        Just as the fact handler functions, the datatype extractor can change the add_fact_kargs dictionary
        and thus change the way in which the fact is created -- usually, this ability is used to change
        the following items in the dictionary:

        - fact_dt_name
        - fact_dt_namespace_uri
        - fact_dt_namespace_name (optional -- the defining part is the uri)
        - fact_dt_kind

        The extractor returns "True" if datatype info was found; otherwise, False is returned
        """

     	if "dtype" in attr_info:
            add_fact_kargs['fact_dt_name'] = attr_info["dtype"]
            add_fact_kargs['fact_dt_namespace_uri'] = 'urn:ietf:params:xml:ns:iodef-1.0'
            add_fact_kargs['fact_dt_namespace_name'] = 'IODEF'
            return True

        return False

    def xml_import(self,
                   filepath=None,
                   xml_content=None,
                   markings=None,
                   identifier_ns_uri=None,
                   **kwargs):
        """
        Import a iodef XML  from file <filepath>.
        You can provide:

        - a list of markings with which all generated Information Objects
           will be associated (e.g., in order to provide provenance function)

        - The uri of a namespace of the identifiers for the generated information objects.
          This namespace identifiers the 'owner' of the object. For example, if importing
          IOCs published by Mandiant (e.g., as part of the APT1 report), chose an namespace
          such  as 'mandiant.com' or similar (and be consistent about it, when importing
          other stuff published by Mandiant).

        The kwargs are not read -- they are present to allow the use of the
        DingoImportCommand class for easy definition of commandline import commands
        (the class passes all command line arguments to the xml_import function, so
        without the **kwargs parameter, an error would occur.
        """

        # Clear state in case xml_import is used several times

        self.__init__()

        # Initialize  default arguments

        # '[]' would be mutable, so we initialize here
        if not markings:
            markings = []

        # Initalizing here allows us to also get the default namespace when
        # explicitly passing 'None' as parameter.

        if identifier_ns_uri:
            self.identifier_ns_uri = identifier_ns_uri
        else:
            self.identifier_ns_uri = 'test'

        # Use the generic XML import customized for  OpenIOC import
        # to turn XML into DingoObjDicts

        import_result =  MantisImporter.xml_import(xml_fname=filepath,
                                                   xml_content=xml_content,
                                                   ns_mapping=self.namespace_dict,
                                                   embedded_predicate=self.embedding_pred,
                                                   id_and_revision_extractor=self.id_and_revision_extractor,
                                                   transformer=self.transformer,
                                                   keep_attrs_in_created_reference=False,
                                                  )


        id_and_rev_info = import_result['id_and_rev_info']
        elt_name = import_result['elt_name']
        elt_dict = import_result['dict_repr']

        embedded_objects = import_result['embedded_objects']

        default_ns = self.namespace_dict.get(elt_dict.get('@@ns',None))

        # Export family information.
        self.iobject_family_name='iodef'
        self.iobject_family_revision_name=''


        # Initialize stack with import_results.

        # First, the result from the top-level import
        pending_stack = [(id_and_rev_info, elt_name,elt_dict)]

        # Then the embedded objects
        for embedded_object in  embedded_objects:
            id_and_rev_info = embedded_object['id_and_rev_info']
            elt_name = embedded_object['elt_name']
            elt_dict = embedded_object['dict_repr']
            pending_stack.append((id_and_rev_info,elt_name,elt_dict))

        if id_and_rev_info['timestamp']:
            ts = id_and_rev_info['timestamp']
        else:
            ts = self.create_timestamp

        for (id_and_rev_info, elt_name, elt_dict) in pending_stack:
            # call the importer that turns DingoObjDicts into Information Objects in the database
            iobject_type_name = elt_name
            iobject_type_namespace_uri = self.namespace_dict.get(elt_dict.get('@@ns',None),DINGOS_GENERIC_FAMILY_NAME)

            if not id_and_rev_info['id']:
                logger.error("Attempt to import object (element name %s) without id -- object is ignored" % elt_name)
                continue
    
            MantisImporter.create_iobject(iobject_family_name = self.iobject_family_name,
                                          iobject_family_revision_name= self.iobject_family_revision_name,
                                          iobject_type_name=iobject_type_name,
                                          iobject_type_namespace_uri=iobject_type_namespace_uri,
                                          iobject_type_revision_name= '',
                                          iobject_data=elt_dict,
                                          uid=id_and_rev_info['id'].split(":")[0],
                                          identifier_ns_uri=id_and_rev_info['id'].split(":")[1],
                                          timestamp = ts,
                                          create_timestamp = self.create_timestamp,
                                          markings=markings,
                                          config_hooks = {'special_ft_handler' : self.fact_handler_list(),
                                                         'datatype_extractor' : self.datatype_extractor,
                                                         'attr_ignore_predicate' : self.attr_ignore_predicate},
                                          namespace_dict=self.namespace_dict,
                                          )









