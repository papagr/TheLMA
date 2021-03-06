"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

This module deals with the creation of worklist files.

AAB
"""
from thelma.tools.writers import CsvWriter
from thelma.tools.utils.base import VOLUME_CONVERSION_FACTOR
from thelma.tools.utils.base import get_trimmed_string
from thelma.tools.utils.base import is_larger_than
from thelma.tools.utils.base import is_smaller_than
from thelma.entities.liquidtransfer import PipettingSpecs
from thelma.entities.liquidtransfer import PlannedWorklist
from thelma.entities.liquidtransfer import TRANSFER_TYPES
from thelma.entities.rack import Plate
from thelma.entities.rack import Rack
from thelma.entities.rack import RackPosition


__docformat__ = 'reStructuredText en'

__all__ = ['WorklistWriter']


class WorklistWriter(CsvWriter):
    """
    An abstract tool for the generation of pipetting worklist files.

    **Return Value:** Stream for an CSV file.
    """

    #: The transfer type supported by this class
    #: (see :class:`thelma.entities.liquidtransfer.TRANSFER_TYPES`).
    TRANSFER_TYPE = None

    def __init__(self, planned_worklist, target_rack, pipetting_specs,
                 ignored_positions=None, parent=None):
        """
        Constructor.

        :param planned_worklist: The worklist for which to create a
            worklist file.
        :type planned_worklist:
            :class:`thelma.entities.liquidtransfer.PlannedWorklist`
        :param target_rack: The rack into which the volumes will be dispensed.
        :type target_rack: :class:`thelma.entities.rack.Rack`
        :param pipetting_specs: Pipetting specs define transfer properties and
            conditions like the transfer volume range.
        :type pipetting_specs:
            :class:`thelma.entities.liquidtransfer.PipettingSpecs`
        :param list ignored_positions: A list of positions (target
            for dilutions and source for transfers; :class:`RackPosition`)
            that are not included in the worklist file.
        """
        CsvWriter.__init__(self, parent=parent)
        #: The planned worklist for which to create a file stream.
        self.planned_worklist = planned_worklist
        #: The rack into which the volumes will be dispensed.
        self.target_rack = target_rack
        #: Pipetting specs define transfer properties and conditions like
        #: the transfer volume range.
        self.pipetting_specs = pipetting_specs
        if ignored_positions is None:
            ignored_positions = []
        #: A list of positions that will not be included in the worklist file
        #: (even if there are planned transfers for them).
        self.ignored_positions = ignored_positions
        #: Maps the containers of the target rack onto rack positions.
        self._target_containers = None
        #: Stores the volume changes for the target rack (mapped onto
        #: rack positions).
        self._target_volumes = None
        #: The maximum volume of a target rack container in ul.
        self._target_max_volume = None
        #: Maps the container of the source rack onto rack position.
        self._source_containers = None
        #: Stores the volume changes for the source rack (mapped onto
        #: rack positions).
        self._source_volumes = None
        #: The minimum dead volume of source rack container in ul.
        self._source_dead_volume = None
        #: The minimum transfer volume used in ul.
        self._min_transfer_volume = None
        #: The maximum transfer volume used in ul.
        self._max_transfer_volume = None
        # Intermediate data storage for errors.
        self._transfer_volume_too_small = None
        self._transfer_volume_too_large = None
        self._source_volume_too_small = None
        self._source_container_missing = None
        self._target_volume_too_large = None
        self._target_container_missing = None

    def reset(self):
        """
        Resets all values except for input values.
        """
        CsvWriter.reset(self)
        self._target_containers = dict()
        self._target_volumes = dict()
        self._target_max_volume = None
        self._source_containers = dict()
        self._source_volumes = dict()
        self._source_dead_volume = None
        # Intermediate data storage for errors.
        self._transfer_volume_too_small = []
        self._transfer_volume_too_large = []
        self._source_volume_too_small = set()
        self._source_container_missing = set()
        self._target_volume_too_large = []
        self._target_container_missing = []

    def _init_column_map_list(self):
        """
        Creates the :attr:`_column_map_list` for the CSV writer.
        """
        self.add_info('Start column generation for worklist file ...')
        self._check_input()
        if not self.has_errors():
            self._init_target_data()
            self._init_source_data()
            self.__check_planned_liquid_transfers()
        if not self.has_errors():
            self.__set_transfer_volume_range()
            self._generate_column_values()
            self._record_errors()
        if not self.has_errors():
            self._init_column_maps()
        if not self.has_errors():
            self.add_info('Column generation completed ...')

    def _check_input(self):
        """
        Checks the input values.
        """
        self.add_debug('Check input values ...')
        if self._check_input_class('planned worklist', self.planned_worklist,
                                   PlannedWorklist):
            if not self.planned_worklist.transfer_type == self.TRANSFER_TYPE:
                msg = 'Unsupported transfer type: %s' \
                       % (self.planned_worklist.transfer_type)
                self.add_error(msg)
        self._check_input_class('target rack', self.target_rack, Rack)
        self._check_input_class('pipetting specs', self.pipetting_specs,
                                PipettingSpecs)

        self._check_input_list_classes('ignored position',
                       self.ignored_positions, RackPosition, may_be_empty=True)

    def _init_target_data(self):
        """
        Initialises the target rack related values and lookups.
        """
        for container in self.target_rack.containers:
            rack_pos = container.position
            self._target_containers[rack_pos] = container
            if container.sample is None:
                self._target_volumes[rack_pos] = 0.0
            else:
                volume = container.sample.volume * VOLUME_CONVERSION_FACTOR
                self._target_volumes[rack_pos] = volume
        if isinstance(self.target_rack, Plate):
            well_specs = self.target_rack.specs.well_specs
            self._target_max_volume = well_specs.max_volume \
                                      * VOLUME_CONVERSION_FACTOR

    def _init_source_data(self):
        """
        Initialises the source rack related values and lookups.
        """
        self.add_error('Abstract method: _init_source_data()')

    def __set_transfer_volume_range(self):
        # Sets the default range for transfers volume, if there are not
        # customized values.
        self.add_debug('Set transfer volume range ...')

        if self._min_transfer_volume is None:
            self._min_transfer_volume = VOLUME_CONVERSION_FACTOR \
                                    * self.pipetting_specs.min_transfer_volume
        if self._max_transfer_volume is None:
            self._max_transfer_volume = VOLUME_CONVERSION_FACTOR \
                                    * self.pipetting_specs.max_transfer_volume

    def _generate_column_values(self):
        """
        This method generates the value lists for the CSV columns.
        """
        self.add_error('Abstract method: _generate_column_values()')

    def __check_planned_liquid_transfers(self):
        # Checks whether all planned transfers in the worklist have the
        # correct type.
        unsupported_transfer_type = []
        for plt in self.planned_worklist:
            if not plt.transfer_type == self.TRANSFER_TYPE:
                unsupported_transfer_type.append(plt)
        if len(unsupported_transfer_type) > 0:
            msg = 'Some transfers planned in the worklist are not supported: ' \
                  '%s. Supported type: %s.' % (unsupported_transfer_type,
                                               self.TRANSFER_TYPE)
            self.add_error(msg)

    def _check_transfer_volume(self, transfer_volume, target_position,
                               source_position=None):
        """
        Checks whether the transfer volume is in a valid volume range,
        whether the target container can take that amount and whether
        there is enough volume in the source container.
        """
        volume = transfer_volume * VOLUME_CONVERSION_FACTOR
        # Check the minimum and maximum transfer volume.
        if is_smaller_than(volume, self._min_transfer_volume):
            error_msg = 'target %s (%.1f ul)' \
                        % (target_position.label, volume)
            self._transfer_volume_too_small.append(error_msg)
            return False
        if self.TRANSFER_TYPE == TRANSFER_TYPES.SAMPLE_TRANSFER \
                        and is_larger_than(volume, self._max_transfer_volume):
            error_msg = 'source %s (%.1f ul)' % (source_position, volume)
            self._transfer_volume_too_large.append(error_msg)
        # Check whether there is enough space in the target well.
        max_volume = \
            self.__get_max_volume_for_target_container(target_position)
        if max_volume is None:
            return False
        sample_volume = self._target_volumes[target_position]
        if is_smaller_than(max_volume, (sample_volume + volume)):
            error_msg = '%s (sample vol: %.1f, transfer vol: %.1f)' \
                        % (target_position, sample_volume, volume)
            self._target_volume_too_large.append(error_msg)
            return False
        # Check whether there is enough liquid in the source well
        if self.TRANSFER_TYPE == TRANSFER_TYPES.SAMPLE_DILUTION:
            return True
        if source_position is None:
            msg = 'You must not pass a None value for the source well ' \
                  'when checking the volumes if you have passed a source ' \
                  'rack!'
            self.add_error(msg)
            return False
        if not self._source_volumes.has_key(source_position):
            self._source_container_missing.add(source_position.label)
            return False
        source_volume = self._source_volumes[source_position]
        source_volume -= volume
        dead_volume = self.__get_dead_volume_for_source_container(
                                                                source_position)
        if is_smaller_than(source_volume, dead_volume):
            self._source_volume_too_small.add(source_position.label)
            return False
        self._source_volumes[source_position] = source_volume
        return True

    def __get_max_volume_for_target_container(self, target_position):
        # Returns the maximum volume for the container at the given
        # target position.
        if self._target_max_volume is None:
            if not self._target_containers.has_key(target_position):
                self._target_container_missing.append(target_position.label)
                return None
            container = self._target_containers[target_position]
            return container.specs.max_volume * VOLUME_CONVERSION_FACTOR
        else:
            return self._target_max_volume

    def __get_dead_volume_for_source_container(self, source_position):
        # Returns the maximum volume for the container at the given
        # target position.
        if self._source_dead_volume is None:
            if not self._source_containers.has_key(source_position):
                self._source_container_missing.add(source_position.label)
                return None
            container = self._source_containers[source_position]
            return container.specs.dead_volume * VOLUME_CONVERSION_FACTOR
        else:
            return self._source_dead_volume

    def _record_errors(self):
        """
        Records errors that have been found during value list creation.
        """
        if len(self._transfer_volume_too_small) > 0:
            msg = 'Some transfer volume are smaller than the allowed minimum ' \
                  'transfer volume of %s ul: %s.' % (self._min_transfer_volume,
                     ', '.join(sorted(self._transfer_volume_too_small)))
            self.add_error(msg)
        if len(self._transfer_volume_too_large) > 0:
            msg = 'Some transfer volume are larger than the allowed maximum ' \
                  'transfer volume of %s ul: %s.' % (self._max_transfer_volume,
                            ', '.join(sorted(self._transfer_volume_too_large)))
            self.add_error(msg)
        if len(self._source_volume_too_small) > 0:
            error_list = sorted(list(self._source_volume_too_small))
            msg = 'Some source containers do not contain enough volume to ' \
                  'provide liquid for all target containers: %s.' \
                   % (', '.join(error_list))
            self.add_error(msg)
        if len(self._source_container_missing) > 0:
            error_list = sorted(list(self._source_container_missing))
            msg = 'Could not find containers for the following source ' \
                  'positions: %s.' % (', '.join(error_list))
            self.add_error(msg)
        if len(self._target_volume_too_large) > 0:
            msg = 'Some target containers cannot take up the transfer volume: ' \
                  '%s. ' % (', '.join(sorted(self._target_volume_too_large)))
            if self._target_max_volume is not None:
                msg += 'Assumed maximum volume per target well: %s ul.' \
                       % (get_trimmed_string(self._target_max_volume))
            self.add_error(msg)
        if len(self._target_container_missing) > 0:
            msg = 'Could not find containers for the following target ' \
                  'positions: %s.' \
                   % (', '.join(sorted(self._target_container_missing)))
            self.add_error(msg)

    def _init_column_maps(self):
        """
        Initialises the CsvColumnParameters object for the
        :attr:`_column_map_list`.
        """
        self.add_error('Abstract method: _init_column_maps()')
