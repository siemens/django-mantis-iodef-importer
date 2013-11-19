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

        # We initialize the namespace dictionary for this importer
        # with the dingos default namespace. In case the XML file
        # does not provide namespace information, the default
        # namespace is used.

        self.namespace_dict = {None: DINGOS_NAMESPACE_URI}


        # Whenever an object is created, we save the creation time.
        # Note that the xml_import function below makes a call to
        # __init__, so the timestamp is set freshly for each
        # call to this function.

        self.create_timestamp = timezone.now()

        # All objects have identifiers, and each identifier needs
        # a namespace. In case we cannot extract one from the
        # xml, we set the default Dingos ID namespace.

        self.identifier_ns_uri = DINGOS_DEFAULT_ID_NAMESPACE_URI

        # We use the list of regular expressions below to
        # extract namespace and revision info from the provided
        # xml namespace. For IODEF, the namespace info should be
        #
        # urn:ietf:params:xml:ns:iodef-1.0
        #
        # from which we extract the following:
        #
        # - family namespace (used as namespace for the Incident objects)::
        #
        #       urn:ietf:params:xml:ns:iodef
        #
        #   I.e., we leave away the version/revision info such that
        #   Incident objects from higher revisions of IODEF fall into
        #   the same InfoObject type.
        #
        # - family: iodef
        # - revision: 1.0


        self.RE_LIST_NS_TYPE_FROM_NS_URL = [
        re.compile(
           "(?P<family_ns>urn:ietf:params:xml:ns:(?P<family>(?P<family_tag>[^-]*)))-(?P<revision>.*)")
        ]

        # We provide default values for family name and revision in case
        # there is no namespace info.

        self.iobject_family_name = 'iodef'
        self.iobject_family_revision_name = ''


    #
    # First of all, we define functions for the hooks provided to us
    # by the DINGO xml-import.
    #

    def embedding_pred(self, parent, child, ns_mapping):
        """

        Predicate for recognizing inlined content in an XML; to
        be used for DINGO's xml-import hook 'embedded_predicate'.
        The question this predicate must answer is whether
        the child should be extracted into a separate object.

        The function returns either
        - False (the child is not to be extracted)
        - True (the child is extracted but nothing can be inferred
          about what kind of object is extracted)
        - a string giving some indication about the object type
          (if nothing else is known: the name of the element)

        Note: the 'parent' and 'child' arguments are XMLNodes as defined
        by the Python libxml2 bindings. If you have never worked with these, have a look at

        - Mike Kneller's brief intro: http://mikekneller.com/kb/python/libxml2python/part1
        - the functions in django-dingos core.xml_utils module

        For iodef import, we extract only Incident elements.
        """

        values = extract_attributes(parent, prefix_key_char='@')

        # Incident - see RFC5070 page 12
        if child.name == 'Incident':
            return child.name
        return False


    def id_and_revision_extractor(self, xml_elt):
        """
        Function for generating a unique identifier for extracted embedded content;
        to be used for DINGO's xml-import hook 'embedded_id_gen'.

        This function is called

        - for the top-level node of the XML to be imported.

        - for each node at which an embedded object is extracted from the XML
          (when this occurs is governed by the following function, the
          embedding_pred

        It must return an identifier and, where applicable, a revision and or timestamp;
        in the form of a dictionary {'id':<identifier>, 'timestamp': <timestamp>}.
        How you format the identifier is up to you, because you will have to adopt
        the code below in function xml_import such that the Information Objects
        are created with the proper identifier (consisting of qualifying namespace
        and uri.

        Note: the xml_elt is an XMLNode defined by the Python libxml2 bindings. If you
        have never worked with these, have a look at

        - Mike Kneller's brief intro: http://mikekneller.com/kb/python/libxml2python/part1
        - the functions in django-dingos core.xml_utils module
        Function for generating a unique identifier for extracted embedded content;
        to be used for DINGO's xml-import hook 'embedded_id_gen'.

        For the iodef import, we only extract embedded 'Incident' objects and
        therefore must teach this function to extract identifier and
        timestamp for incidents.
        """

        result = {'id': None, 'timestamp': None}

        if not xml_elt.name == "Incident":
            return result

        # So we have an Incident node. These have the following shape::
        #
        #    <Incident purpose="mitigation">
        #     <IncidentID name="csirt.example.com">908711</IncidentID>
        #     <ReportTime>2006-06-08T05:44:53-05:00</ReportTime>
        #     <Description>Large bot-net</Description>
        #     ...
        #
        # So we must find the child nodes 'IncidentID' and 'ReportTime' ...

        child = xml_elt.children

        found_id = False
        found_ts = False

        while child:
            attributes = extract_attributes(child, prefix_key_char='')

            if child.name == "IncidentID":
                result['id'] = '%s:%s' % (attributes.get('name'), child.content)
                found_id = True

            elif child.name == "ReportTime":
                naive = parse_datetime(child.content)
                if not timezone.is_aware(naive):
                    aware = timezone.make_aware(naive, timezone.utc)
                else:
                    aware = naive
                result['timestamp'] = aware

                found_ts = True

            if found_id and found_ts:
                break

            child = child.next

        return result


    def transformer(self, elt_name, contents):
        """
        This function is called for each DingoObjectDict
        that is created during the XML import process:
        it is given the element name and the DingObject Dict
        for the contents found under that element.

        We do not need to transform anything for iodef import.
        If you want to see an transfomer in action, have a look
        at the importer for OpenIOC.

        """
        return (elt_name, contents)


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


        For the iodef import, do not need much extra handling: all that we do
        is to split comma-separated port lists: we do this here to showcase the
        use of the fact_handler_list and also to show that the DINGOS datamodel allows
        one fact to be associated with several values. Whether you want to
        keep the port lists in one piece depens on how you want to process the imported information ...
        """

        return [(lambda fact, attr_info: fact['term'].split('/')[-1] == "Portlist", self.iodef_portlist_fact_handler)]

    def iodef_portlist_fact_handler(self, enrichment, fact, attr_info, add_fact_kargs):
        """
        Handler for dealing with 'Portlist' values.

        Comma-separated lists are allowed within the Portlist-node in IODEF.

        This handler is called for elements concerning a portlist-node
        such as the following example:

        <Service ip_protocol="6">
            <Portlist>60524,60526,60527,60531</Portlist>
        </Service>


        See above in the comment for the 'fact_handler_list' for an explanation of
        the signature of handler functions.
        """

        add_fact_kargs['values'] = fact['value'].split(',')
        return True


    def attr_ignore_predicate(self, fact_dict):
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

        if 'dtype' in fact_dict['attribute']:
            # We remove dtype attributes, because we have stored the
            # associated information in the fact data type (see datatype extractor below)
            return True
        return False

    def datatype_extractor(self, iobject, fact, attr_info, namespace_mapping, add_fact_kargs):
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

        # iodef provides for some values datattype information via the 'dtype' attribute.
        # We therefore read out this attribute to derive dtype information.

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
          This namespace identifiers the 'owner' of the object. For iodef import, this
          should not be necessary, because the XML schema makes sure that each
          Inicdent is associated with ownership information via the 'name' attribute.

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

        # Use the generic XML import customized for  OpenIOC import
        # to turn XML into DingoObjDicts

        import_result = MantisImporter.xml_import(xml_fname=filepath,
                                                  xml_content=xml_content,
                                                  ns_mapping=self.namespace_dict,
                                                  embedded_predicate=self.embedding_pred,
                                                  id_and_revision_extractor=self.id_and_revision_extractor,
                                                  transformer=self.transformer,
                                                  keep_attrs_in_created_reference=False,
        )

        # The result is of the following form::
        #
        #
        #   {'id_and_rev_info': Id and revision info of top-level element; for iodef, we always have
        #                       {'id':None, 'timestamp':None}, because the  <IODEF-Document> element
        #                       carries no identifier or timestamp
        #    'elt_name': Element name of top-level element, for iodef always 'IODEF-Document'
        #    'dict_repr': Dictionary representation of IODEF XML, minus the embedded Incident objects
        #    'embedded_objects': List of embedded objects, as dictionary
        #                           {"id_and_revision_info": id and revision info of extracted object,
        #                            "elt_name": Element name (for IODEF always 'Incident'),
        #                            "dict_repr" :  dictionary representation of XML of embedded object
        #                           }
        #    'unprocessed' : List of unprocessed embedded objects (not used for iodef import
        #    'file_content': Content of imported file (or, if content was passed instead of a file name,
        #                    the original content)}

        id_and_rev_info = import_result['id_and_rev_info']
        elt_name = import_result['elt_name']
        elt_dict = import_result['dict_repr']

        embedded_objects = import_result['embedded_objects']

        default_ns = self.namespace_dict.get(elt_dict.get('@@ns', None))

        # Here, we could try to extract the family name and version from
        # the namespace information, but we do not do that for now.

        ns_info = search_by_re_list(self.RE_LIST_NS_TYPE_FROM_NS_URL,default_ns)

        if ns_info:
            if 'family' in ns_info:
                self.iobject_family_name = ns_info['family']
            if 'revision' in ns_info:
                self.iobject_family_revision_name = ns_info['revision']

        # Initialize stack with import_results.

        # First, the result from the top-level import
        pending_stack = [(id_and_rev_info, elt_name, elt_dict)]

        # Then the embedded objects
        for embedded_object in embedded_objects:
            id_and_rev_info = embedded_object['id_and_rev_info']
            elt_name = embedded_object['elt_name']
            elt_dict = embedded_object['dict_repr']
            pending_stack.append((id_and_rev_info, elt_name, elt_dict))


        for (id_and_rev_info, elt_name, elt_dict) in pending_stack:
            # call the importer that turns DingoObjDicts into Information Objects in the database

            if id_and_rev_info['timestamp']:
                ts = id_and_rev_info['timestamp']
            else:
                ts = self.create_timestamp

            iobject_type_name = elt_name

            ns_info = search_by_re_list(self.RE_LIST_NS_TYPE_FROM_NS_URL,default_ns)

            iobject_type_namespace_uri = None
            iobject_type_revision_name = None

            if ns_info:
                if 'family_ns' in ns_info:
                    iobject_type_namespace_uri = ns_info['family_ns']
                if 'revision' in ns_info:
                    iobject_type_revision_name = ns_info['revision']

            if not iobject_type_namespace_uri:
                iobject_type_namespace_uri = self.namespace_dict.get(elt_dict.get('@@ns', None), DINGOS_GENERIC_FAMILY_NAME)

            if not id_and_rev_info['id']:
                logger.error("Attempt to import object (element name %s) without id -- object is ignored" % elt_name)
                continue

            MantisImporter.create_iobject(iobject_family_name=self.iobject_family_name,
                                          iobject_family_revision_name=self.iobject_family_revision_name,
                                          iobject_type_name=iobject_type_name,
                                          iobject_type_namespace_uri=iobject_type_namespace_uri,
                                          iobject_type_revision_name=iobject_type_revision_name,
                                          iobject_data=elt_dict,
                                          uid=id_and_rev_info['id'].split(":")[0],
                                          identifier_ns_uri=id_and_rev_info['id'].split(":")[1],
                                          timestamp=ts,
                                          create_timestamp=self.create_timestamp,
                                          markings=markings,
                                          config_hooks={'special_ft_handler': self.fact_handler_list(),
                                                        'datatype_extractor': self.datatype_extractor,
                                                        'attr_ignore_predicate': self.attr_ignore_predicate},
                                          namespace_dict=self.namespace_dict,
            )









