"""
Experiment resources.

FOG Mar 21, 2011
"""

from datetime import datetime
from everest.querying.specifications import AscendingOrderSpecification
from everest.querying.specifications import DescendingOrderSpecification
from everest.representers.dataelements import DataElementAttributeProxy
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from everest.resources.staging import create_staging_collection
from pyramid.httpexceptions import HTTPBadRequest
from thelma.automation.tools.metadata.ticket import IsoRequestTicketDescriptionRemover
from thelma.automation.tools.metadata.ticket \
    import IsoRequestTicketDescriptionUpdater
from thelma.automation.tools.metadata.ticket import IsoRequestTicketActivator
from thelma.automation.tools.metadata.ticket import IsoRequestTicketCreator
from thelma.automation.tools.stock.base import STOCKMANAGEMENT_USER
from thelma.interfaces import IExperiment
from thelma.interfaces import IExperimentDesign
from thelma.interfaces import IExperimentDesignRack
from thelma.interfaces import IExperimentJob
from thelma.interfaces import IExperimentMetadata
from thelma.interfaces import IExperimentMetadataType
from thelma.interfaces import IExperimentRack
from thelma.interfaces import IIsoRequest
from thelma.interfaces import IMoleculeDesignPoolSet
from thelma.interfaces import IPlate
from thelma.interfaces import IRack
from thelma.interfaces import IRackLayout
from thelma.interfaces import IRackShape
from thelma.interfaces import IRackSpecs
from thelma.interfaces import ISubproject
from thelma.interfaces import ITag
from thelma.models.racklayout import RackLayout
from thelma.models.utils import get_current_user
from thelma.resources.base import RELATION_BASE_URL
import logging
# from thelma.models.experiment import ExperimentDesignRack

__docformat__ = 'reStructuredText en'

__author__ = 'F Oliver Gathmann'
__date__ = '$Date: 2013-05-13 14:13:15 +0200 (Mon, 13 May 2013) $'
__revision__ = '$Rev: 13338 $'
__source__ = '$URL::                                                          $'

__all__ = ['ExperimentMetadataTypeMember',
           'ExperimentCollection',
           'ExperimentDesignCollection',
           'ExperimentDesignMember',
           'ExperimentDesignRackCollection',
           'ExperimentDesignRackMember',
           'ExperimentMember',
           'ExperimentMetadataCollection',
           'ExperimentMetadataMember',
           'ExperimentRackCollection',
           'ExperimentRackMember',
           ]


class ExperimentMetadataTypeMember(Member):
    relation = '%s/experiment-metadata-type' % RELATION_BASE_URL
    title = attribute_alias('display_name')
    display_name = terminal_attribute(str, 'display_name')


class ExperimentDesignRackMember(Member):
    relation = "%s/experiment-design-rack" % RELATION_BASE_URL
    title = attribute_alias('label')
    label = terminal_attribute(str, 'label')
    rack_layout = member_attribute(IRackLayout, 'layout')
    tags = collection_attribute(ITag, 'tags')


class ExperimentDesignRackCollection(Collection):
    title = 'Experiment Design Racks'
    root_name = 'experiment-design-racks'
    description = 'Manage experiment design racks'
#    default_order = asc('label')


class ExperimentDesignMember(Member):
    relation = "%s/experiment-design" % RELATION_BASE_URL
    title = terminal_attribute(str, 'slug')
    rack_shape = member_attribute(IRackShape, 'rack_shape')
    experiment_design_racks = collection_attribute(IExperimentDesignRack,
                                                   'design_racks')
    experiments = collection_attribute(IExperiment, 'experiments')
    experiment_metadata = member_attribute(IExperimentMetadata,
                                           'experiment_metadata')


    def __getitem__(self, name):
        if name == 'experiment-design-racks':
            return self.experiment_design_racks
        elif name == 'experiment_metadata':
            return self.experiment_metadata
        else:
            raise KeyError(name)

    def update_from_entity(self, new_entity):
        entity = self.get_entity()
        while entity.design_racks:
            entity.design_racks.pop()
        while new_entity.design_racks:
            new_rack = new_entity.design_racks.pop()
            entity.design_racks.append(new_rack)
#            ws = rack.worklist_series
#            rack.worklist_series = None
#            # remove the back reference to avoid conflicts
#            new_rack = ExperimentDesignRack(rack.label,
#                                            rack.layout,
#                                            worklist_series=ws)
#            entity.design_racks.append(new_rack)
        entity.rack_shape = new_entity.rack_shape
        entity.worklist_series = new_entity.worklist_series


class ExperimentDesignCollection(Collection):
    title = 'Experiment Designs'
    root_name = 'experiment-designs'
    description = 'Manage experiment designs'
    default_order = AscendingOrderSpecification('label')


class ExperimentMember(Member):
    relation = '%s/experiment' % RELATION_BASE_URL
    label = terminal_attribute(str, 'label')
    title = attribute_alias('label')
    destination_rack_specs = member_attribute(IRackSpecs,
                                              'destination_rack_specs')
    source_rack = member_attribute(IRack, 'source_rack')
    experiment_design = member_attribute(IExperimentDesign,
                                         'experiment_design')
    experiment_racks = collection_attribute(IExperimentRack,
                                            'experiment_racks')
    experiment_job = member_attribute(IExperimentJob, 'job')
    experiment_metadata_type = \
        member_attribute(IExperimentMetadataType,
            'experiment_design.experiment_metadata.experiment_metadata_type')

    def __getitem__(self, name):
        if name == 'experiment-racks':
            return self.experiment_racks
        else:
            raise KeyError(name)


class ExperimentCollection(Collection):
    title = 'Experiments'
    root_name = 'experiments'
    description = 'Manage experiments'
    default_order = AscendingOrderSpecification('label')


class ExperimentMetadataMember(Member):
    relation = '%s/experiment-metadata' % RELATION_BASE_URL
    label = terminal_attribute(str, 'label')
    title = attribute_alias('label')
    ticket_number = terminal_attribute(int, 'ticket_number')
    subproject = member_attribute(ISubproject, 'subproject')
    number_replicates = terminal_attribute(int, 'number_replicates')
    molecule_design_pool_set = member_attribute(IMoleculeDesignPoolSet,
                                                'molecule_design_pool_set',
                                                is_nested=True)
    experiment_design = member_attribute(IExperimentDesign,
                                         'experiment_design',
                                         is_nested=True)
    experiment_design_racks = \
            collection_attribute(IExperimentDesignRack,
                                 'experiment_design.design_racks')
    iso_request = member_attribute(IIsoRequest, 'iso_request')
    creation_date = terminal_attribute(datetime, 'creation_date')
    experiment_metadata_type = member_attribute(IExperimentMetadataType,
                                                'experiment_metadata_type')

    def __getitem__(self, name):
        if name == 'tags':
            tags_dict = {}
            if not self.experiment_design is None:
                for rack in self.experiment_design.experiment_design_racks:
                    for tp in rack.rack_layout.tagged_rack_position_sets:
                        for tag in tp.tags:
                            tags_dict[tag.get_entity().slug] = tag
            tag_coll = create_staging_collection(ITag)
            for tag in tags_dict.values():
                tag_coll.add(tag)
            result = tag_coll
        else:
            result = Member.__getitem__(self, name)
        return result

    @classmethod
    def create_from_entity(cls, entity):
        if entity.ticket_number is None:
            # Create a new ticket and attach the ticket number.
            user = get_current_user()
            ticket_creator = \
                IsoRequestTicketCreator(requester=user,
                                        experiment_metadata=entity)
            entity.ticket_number = \
                cls.__run_trac_tool(ticket_creator,
                                    'Could not update the ticket: %s.')
        return cls(entity)

    def update_from_data(self, data_element):
        prx = DataElementAttributeProxy(data_element)
        self_entity = self.get_entity()
        changed_num_reps = (prx.number_replicates != self.number_replicates)
        changed_em_type = (prx.experiment_metadata_type.get('id') \
                           != self.experiment_metadata_type.id)
        if changed_em_type or changed_num_reps:
            if not self_entity.experiment_design is None:
                # invalidate data to force a fresh upload of the XLS file
                self_entity.experiment_design.experiment_design_racks = []
                self_entity.experiment_design.worklist_series = None
            if not self_entity.iso_request is None:
                shape = self_entity.iso_request.iso_layout.shape
                new_layout = RackLayout(shape=shape)
                self_entity.iso_request.iso_layout = new_layout
                self_entity.iso_request.owner = ''
        Member.update_from_data(self, data_element)
        # Perform appropriate Trac updates.
        if not self_entity.iso_request is None:
            if self.iso_request.owner == STOCKMANAGEMENT_USER:
                ticket_activator = IsoRequestTicketActivator(
                                            experiment_metadata=self_entity)
                self.__run_trac_tool(ticket_activator,
                                     'Could not update the ticket: %s.')
            else:
                if changed_em_type or changed_num_reps:
                    trac_updater = IsoRequestTicketDescriptionRemover(
                                  experiment_metadata=self_entity,
                                  changed_num_replicates=changed_num_reps,
                                  changed_em_type=changed_em_type)
                else:
                    url = 'http://thelma/public//LOUICe.html#' \
                          + self.path
                    iso_url = 'http://thelma/public//LOUICe.html#' \
                              + self.iso_request.path
                    trac_updater = IsoRequestTicketDescriptionUpdater(
                                        experiment_metadata=self_entity,
                                        experiment_metadata_link=url,
                                        iso_request_link=iso_url)
                self.__run_trac_tool(trac_updater,
                                     'Could not update the ticket: %s.')

    @classmethod
    def __run_trac_tool(cls, tool, error_msg_text):
        tool.send_request()
        if not tool.transaction_completed():
            exc_msg = str(tool.get_messages(logging.ERROR))
            raise HTTPBadRequest(error_msg_text % exc_msg).exception
        return tool.return_value


class ExperimentMetadataCollection(Collection):
    title = 'Experiment Metadata'
    root_name = 'experiment-metadatas'
    description = 'Manage the experiment metadata'
    default_order = DescendingOrderSpecification('creation_date')


class ExperimentRackMember(Member):
    relation = '%s/experiment-rack' % RELATION_BASE_URL
    experiment = member_attribute(IExperiment, 'experiment')
    design_rack = member_attribute(IExperimentDesignRack, 'design_rack')
    plate = member_attribute(IPlate, 'rack')
    source_rack = member_attribute(IRack, 'source_rack')


class ExperimentRackCollection(Collection):
    title = 'Cell Plates'
    root_name = 'experiment-racks'
    description = 'Manage cell plates'
