"""
Base tools, for stock rack related tasks involved in lab ISO processing.

AAB
"""
from everest.entities.utils import get_root_aggregate
from thelma.automation.tools.base import BaseAutomationTool
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayout
from thelma.automation.tools.iso.lab.base import FinalLabIsoLayoutConverter
from thelma.automation.tools.iso.lab.base import LABELS
from thelma.automation.tools.iso.lab.base import LabIsoPrepLayoutConverter
from thelma.automation.tools.iso.base import IsoRackContainer
from thelma.automation.tools.semiconstants \
    import get_pipetting_specs_biomek_stock
from thelma.automation.tools.semiconstants import get_pipetting_specs_cybio
from thelma.automation.tools.utils.base import CONCENTRATION_CONVERSION_FACTOR
from thelma.automation.tools.utils.base import add_list_map_element
from thelma.interfaces import ITubeRack
from thelma.models.iso import IsoJobStockRack
from thelma.models.iso import IsoSectorStockRack
from thelma.models.iso import IsoStockRack
from thelma.models.iso import LabIso
from thelma.models.job import IsoJob
from thelma.models.liquidtransfer import PlannedWorklist
from thelma.models.liquidtransfer import TRANSFER_TYPES
from thelma.models.liquidtransfer import WorklistSeries

__docformat__ = 'reStructuredText en'

__all__ = ['_StockRackAssigner',
           'StockTubeContainer']


class _StockRackAssigner(BaseAutomationTool):
    """
    Abstract base tool for tools that assign stock racks to lab ISOs or ISO
    jobs.

    **Return Value:** depends on the subclass
    """

    #: The entity class supported by this assigner.
    _ENTITY_CLS = None

    def __init__(self, entity, rack_barcodes, **kw):
        """
        Constructor:

        :param entity: The ISO or the ISO job to which to assign the racks.
        :type entity: :class:`LabIso` or :class:`IsoJob`
            (see :attr:`_ENTITY_CLS).

        :param rack_barcodes: The barcodes for the racks to be assigned.
        :type rack_barcodes: list of barcodes (:class:`basestring`)
        """
        BaseAutomationTool.__init__(self, depending=False, **kw)

        #: The ISO or the ISO job to which to assign the racks.
        self.entity = entity
        #: The barcodes for the racks to be assigned.
        self.rack_barcodes = rack_barcodes

        #: The lab ISO requests the entity belongs to.
        self._iso_request = None
        #: Maps tube racks onto barcodes (required for stock racks).
        self._barcode_map = None

        #: The ISO plate layouts of the ISO (job) plates mapped onto plate
        #: labels. For the final plate layout there is only one layout
        #: (mapped onto the :attr:`LABELS.ROLE_FINAL` marker).
        self._plate_layouts = None
        #: The :class:`StockTubeContainer` objects mapped onto pools.
        self._stock_tube_containers = None

        #: The :class:`IsoRackContainer` for each involved plate or rack
        #: mapped onto label
        self._rack_containers = None

        #: The stock rack layout for each stock rack (marker).
        self._stock_rack_layouts = None
        #: The worklist series for the stock transfers mapped onto stock
        #: rack label.
        self.__stock_transfer_series = None

    def reset(self):
        BaseAutomationTool.reset(self)
        self._iso_request = None
        self._barcode_map = dict()
        self._plate_layouts = dict()
        self._stock_tube_containers = dict()
        self._rack_containers = dict()
        self._stock_rack_layouts = dict()
        self.__stock_transfer_series = dict()

    def run(self):
        self.reset()
        self.add_info('Start planning XL20 run ...')

        self._check_input()
        if not self.has_errors():
            self.__get_tube_racks()
            self._get_layouts()
        if not self.has_errors(): self._find_starting_wells()
        if not self.has_errors(): self._find_stock_tubes()
        if not self.has_errors(): self.__assign_stock_racks()
        if not self.has_errors(): self._create_output()

    def _check_input(self):
        """
        Checks the initialisation values.
        """
        self.add_debug('Check input values ...')

        if self._check_input_class('entity', self.entity, self._ENTITY_CLS):
            self._iso_request = self.entity.iso_request
        self._check_input_list_classes('barcode', self.rack_barcodes,
                                       basestring)

    def __get_tube_racks(self):
        """
        Fetches the tube racks for the passed barcodes from the DB.
        """
        self.add_debug('Fetch racks for barcodes ...')

        non_empty = []
        tube_rack_agg = get_root_aggregate(ITubeRack)

        for barcode in self.rack_barcodes:
            if len(barcode) < 1: continue
            rack = tube_rack_agg.get_by_slug(barcode)
            if rack is None:
                msg = 'Rack %s has not been found in the DB!' % (barcode)
                self.add_error(msg)
            elif len(rack.containers) > 0:
                non_empty.append(barcode)
            else:
                self._barcode_map[barcode] = rack

        if len(non_empty) > 0:
            non_empty.sort()
            msg = 'The following racks you have chosen are not empty: %s.' \
                  % (self._get_joined_str(non_empty))
            self.add_error(msg)

        if not self.has_errors() and \
                    (len(self._barcode_map) < self.entity.number_stock_racks):
            msg = 'The number of stock rack barcodes is too low! ' \
                  'Expected: %i, found: %i.' % (self.entity.number_stock_racks,
                                                len(self._barcode_map))
            self.add_error(msg)

    def _get_layouts(self):
        """
        Fetches the layouts of each plate involved in the generation of
        the :attr:`entity`.
        """
        raise NotImplementedError('Abstract method.')

    def _store_plate_layout(self, label, converter, error_label):
        """
        Helper function running the passed converter. In case of failure, an
        error message is recorded. Otherwise the resulting layouts is stored
        in the :attr:`_plate_layouts` map.
        """
        layout = converter.get_result()
        if layout is None:
            msg = 'Error when trying to convert layout for %s.' % (error_label)
            self.add_error(msg)
        else:
            self._plate_layouts[label] = layout

    def _store_final_plate_data(self, iso):
        """
        Helper function creating and storing a rack container of all final
        plates of an ISO. The rack markers for aliquot and library plates
        need to be distinguished.
        """
        for fp in iso.final_plates:
            self._store_rack_container(fp.rack, role=LABELS.ROLE_FINAL)

    def _store_rack_container(self, rack, role, label=None, rack_marker=None):
        """
        Helper function creating a :class:`IsoRackContainer` for a
        rack. The containers are store in the :attr:`_rack_containers` map.
        """
        if label is None: label = rack.label
        if rack_marker is None:
            values = LABELS.parse_rack_label(label)
            rack_marker = values[LABELS.MARKER_RACK_MARKER]
        rack_container = IsoRackContainer(rack=rack, label=label, role=role,
                                          rack_marker=rack_marker)
        self._rack_containers[label] = rack_container

    def _find_starting_wells(self):
        """
        Searches the stored layouts for starting wells. The data is stored in
        :class:`StockTubeContainer` objects.
        """
        self.add_debug('Search for starting wells ...')

        final_layout_copy_number = len(self._rack_containers[LABELS.ROLE_FINAL])
        for plate_label, layout in self._plate_layouts.iteritems():
            is_final_plate = isinstance(layout, FinalLabIsoLayout)
            for_job = isinstance(self.entity, IsoJob)
            for plate_pos in layout.get_sorted_working_positions():
                if not plate_pos.is_starting_well: continue
                if is_final_plate and not (plate_pos.for_job == for_job):
                    continue
                pool = plate_pos.molecule_design_pool
                if self._stock_tube_containers.has_key(pool):
                    container = self._stock_tube_containers[pool]
                else:
                    container = StockTubeContainer.from_plate_position(
                                            plate_pos, final_layout_copy_number)
                    self._stock_tube_containers[pool] = container
                if is_final_plate:
                    container.add_final_position(plate_pos)
                else:
                    container.add_preparation_position(plate_label, plate_pos)

    def _find_stock_tubes(self):
        """
        Assigns tubes to the stock tube containers. At this, it must be checked
        whether the tubes volumes are still sufficient.
        """
        raise NotImplementedError('Abstract method.')

    def __assign_stock_racks(self):
        """
        Each stock rack needs a layout and a worklist series.
        """
        self.add_debug('Attach stock racks ...')

        self._create_stock_rack_layouts()
        self.__create_stock_rack_worklist_series()
        self.__create_stock_rack_entities()

    def _create_stock_rack_layouts(self):
        """
        Generates the :class:`StockRackLayout` for each stock rack.
        """
        raise NotImplementedError('Abstract method.')

    def __create_stock_rack_worklist_series(self):
        """
        The transfer for each worklist series are derived from the stock
        rack layouts.
        """
        ticket_number = self._iso_request.experiment_metadata.ticket_number
        robot_specs = self._get_stock_transfer_pipetting_specs()
        for sr_marker, sr_layout in self._stock_rack_layouts.iteritems():
            worklist_series = WorklistSeries()
            for rack_marker in self.__get_sorted_plate_markers():
                transfers = []
                for sr_pos in sr_layout.get_working_positions():
                    psts = sr_pos.get_planned_sample_transfers(rack_marker)
                    transfers.extend(psts)
                if len(transfers) < 1: continue
                wl_index = len(worklist_series)
                wl_label = LABELS.create_worklist_label(ticket_number,
                                 worklist_number=wl_index,
                                 target_rack_marker=rack_marker,
                                 source_rack_marker=sr_marker)
                worklist = PlannedWorklist(label=wl_label,
                               transfer_type=TRANSFER_TYPES.SAMPLE_TRANSFER,
                               planned_liquid_transfers=transfers,
                               pipetting_specs=robot_specs)
                worklist_series.add_worklist(wl_index, worklist)
            self.__stock_transfer_series[sr_marker] = worklist_series

    def _get_stock_transfer_pipetting_specs(self):
        """
        Returns the :class:`PipettingSpecs` for the stock transfer.
        """
        raise NotImplementedError('Abstract method.')

    def __get_sorted_plate_markers(self):
        """
        The final ISO plate is the last one. Its key in the layout is list
        is the :attr:`LABELS.ROLE_FINAL` marker, they are therefore not found
        in the rack container map (which uses labels as keys).
        Preparation plates are ordered by name.
        """
        ordered_labels = []
        final_labels = []
        for plate_label in self._plate_layouts.keys():
            if self._rack_containers.has_key(plate_label):
                rack_container = self._rack_containers[plate_label]
                ordered_labels.append(rack_container.rack_marker)
            else:
                # final plates are mapped on plate labels in the rack container
                # map and and on the role solely in the layout map
                final_labels.append(plate_label)

        return sorted(ordered_labels) + sorted(final_labels)

    def __create_stock_rack_entities(self):
        """
        The worklist series and rack layouts have already been generated.
        """
        self._clear_entity_stock_racks()

        stock_rack_map = self._get_stock_rack_map()
        for stock_rack_marker, barcode in stock_rack_map.iteritems():
            kw = self.__get_stock_rack_base_kw(stock_rack_marker, barcode)
            stock_rack = self._create_stock_rack_entity(stock_rack_marker, kw)
            self._store_rack_container(stock_rack.rack, LABELS.ROLE_STOCK,
                                       stock_rack.label)

    def _clear_entity_stock_racks(self):
        """
        Removes all stock racks that might have been set previously from the
        entity.
        """
        raise NotImplementedError('Abstract method.')

    def _get_stock_rack_map(self):
        """
        Returns a map containing the rack barcode for each stock rack marker.
        """
        raise NotImplementedError('Abstract method.')

    def __get_stock_rack_base_kw(self, stock_rack_marker, rack_barcode):
        """
        Helper function returning the keyword dictionary for a
        :class:`StockRack` entity. It contains values for all shared keywords.
        """
        tube_rack = self._barcode_map[rack_barcode]
        rack_layout = self._stock_rack_layouts[stock_rack_marker].\
                      create_rack_layout()
        return dict(rack=tube_rack, rack_layout=rack_layout,
               worklist_series=self.__stock_transfer_series[stock_rack_marker])

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        """
        Creates and returns the stock rack entity for the passed stock rack
        marker. The common stock rack keywords and values are already part
        of the :param:`base_kw`.
        """
        raise NotImplementedError('Abstract method.')

    def _create_output(self):
        """
        Sets the returns value for the tool.
        """
        raise NotImplementedError('Abstract method.')


class _StockRackAssignerIsoJob(_StockRackAssigner): #pylint: disable=W0223
    """
    A base class for stock rack assigners dealing with ISO jobs.

    This class is sort of an add-on. It is not supposed to be used as single
    super class. Comprised are entity specific data but no rack or tube picking.

    **Return Value:** depends on the subclass
    """
    _ENTITY_CLS = IsoJob

    def _get_layouts(self):
        """
        The final layouts for all ISOs are compared and then a reference
        layout is picked.
        For job preparation plates, both layout and racks are stored. For
        the included ISOs only the racks are registered.

        """
        for prep_plate in self.entity.iso_job_preparation_plates:
            converter = LabIsoPrepLayoutConverter(log=self.log,
                                            rack_layout=prep_plate.rack_layout)
            plate_label = prep_plate.rack.label
            error_label = 'job preparation plate "%s"' % (prep_plate.rack.label)
            self._store_plate_layout(plate_label, converter, error_label)
            self._store_rack_container(prep_plate.rack,
                                       LABELS.ROLE_PREPARATION_JOB, plate_label)

        final_layouts = dict()
        for iso in self.entity.isos:
            converter = FinalLabIsoLayoutConverter(log=self.log,
                                            rack_layout=iso.rack_layout)
            error_label = 'final plate layout for ISO "%s"' % (iso.label)
            self._store_plate_layout(iso.label, converter, error_label)
            self._store_final_plate_data(iso)
            final_layouts[iso.label] = self._plate_layouts[iso.label]
            for ipp in iso.iso_preparation_plates:
                self._store_rack_container(ipp.rack,
                                           role=LABELS.ROLE_PREPARATION_ISO)

        self.__compare_final_layouts(final_layouts)

    def __compare_final_layouts(self, final_layouts):
        """
        Assures that the job positions for all final layouts are equal
        and chooses a references ISO. The reference ISO will replace the
        final ISO layout for the different ISOs in the :attr:`_plate_layouts`
        map. The references layout can be accessed via
        :attr:`LABELS.ROLE_FINAL`.
        """
        reference_positions = None
        reference_iso = None
        differing_isos = []
        for iso_label in sorted(final_layouts.keys()):
            final_layout = final_layouts[iso_label]
            job_positions = []
            for final_pos in final_layout.get_sorted_working_positions():
                if final_pos.from_job and final_pos.is_starting_well:
                    job_positions.append(final_pos)
            if reference_positions is None:
                reference_positions = job_positions
                reference_iso = iso_label
            elif not reference_positions == job_positions:
                differing_isos.append(iso_label)

        if len(differing_isos) > 0:
            msg = 'The final layout for the ISOs in this job differ! ' \
                  'Reference ISO: %s. Differing ISOs: %s.' \
                  % (reference_iso, self._get_joined_str(differing_isos))
            self.add_error(msg)
        else:
            final_role = LABELS.ROLE_FINAL
            self._plate_layouts[final_role] = final_layout[reference_iso]
            for iso_label in final_layouts.keys():
                del self._plate_layouts[iso_label]

    def _find_starting_wells(self):
        _StockRackAssigner._find_starting_wells(self)

        if len(self._stock_tube_containers) < 1:
            msg = 'You do not need an XL20 worklist for this ISO job because ' \
                  'all pools are prepared directly via the ISO processing.'
            self.add_error(msg)

    def _get_stock_transfer_pipetting_specs(self):
        """
        For jobs we always use the BioMek.
        """
        return get_pipetting_specs_biomek_stock()

    def _clear_entity_stock_racks(self):
        self.entity.iso_job_stock_racks = []

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        """
        All stock racks are :class:`IsoJobStockRack` entities
        """
        base_kw['iso_job'] = base_kw
        return IsoJobStockRack(**base_kw)


class _StockRackAssignerLabIso(_StockRackAssigner): #pylint: disable=W0223
    """
    A base class for stock rack assigners dealing with lab ISOs.

    This class is sort of an add-on. It is not supposed to be used as single
    super class. Comprised are entity specific data but no rack or tube picking.
    Call :func:`_complete_init` during initialisation.

    **Return Value:** depends on the subclass
    """
    _ENTITY_CLS = LabIso

    def _complete_init(self):
        """
        Add-on method to be called by subclasses during initialization.
        """
        #: Stores the sector index for each stock rack marker. Stock racks
        #: without particular sector are not included.
        self._stock_rack_sectors = None

    def _check_input(self):
        self._stock_rack_sectors = dict() #pylint: disable=W0201

    def _get_layouts(self):
        """
        There is one final layout for the ISO. There can be preparation plates
        as well.
        """
        for prep_plate in self.entity.iso_preparation_plates:
            converter = LabIsoPrepLayoutConverter(log=self.log,
                                            rack_layout=prep_plate.rack_layout)
            plate_label = prep_plate.rack.label
            error_label = 'ISO preparation plate "%s"' % (prep_plate.rack.label)
            self._store_plate_layout(plate_label, converter, error_label)
            self._store_rack_container(prep_plate.rack,
                                       LABELS.ROLE_PREPARATION_ISO, plate_label)

        converter = FinalLabIsoLayoutConverter(log=self.log,
                                            rack_layout=self.entity.rack_layout)
        self._store_plate_layout(LABELS.ROLE_FINAL, converter,
                                 'final ISO plate layout')
        self._store_final_plate_data(self.entity)

    def _get_stock_transfer_pipetting_specs(self):
        """
        Sector stock racks use the CyBio, others use the Biomek.
        """
        if len(self._stock_rack_sectors) > 0:
            return get_pipetting_specs_cybio()
        else:
            return get_pipetting_specs_biomek_stock()

    def _clear_entity_stock_racks(self):
        self.entity.iso_stock_racks = []
        self.entity.iso_sector_stock_racks = []

    def _create_stock_rack_entity(self, stock_rack_marker, base_kw):
        """
        The stock rack can be :class:`IsoStockRack` or
        :class:`IsoSectorStockRack` objects. If there are several final plate
        sectors for a sector stock rack the lowest index is used.
        """
        base_kw['iso'] = self.entity
        if self._stock_rack_sectors.has_key(stock_rack_marker):
            sectors = self._stock_rack_sectors[stock_rack_marker]
            base_kw['sector_index'] = min(sectors)
            stock_rack_cls = IsoSectorStockRack
        else:
            stock_rack_cls = IsoStockRack
        return stock_rack_cls(**base_kw)


class StockTubeContainer(object):
    """
    Helper storage class representing a (requested and/or picked) stock tube.
    """

    def __init__(self, pool, position_type, requested_tube_barcode,
                 expected_rack_barcode, final_position_copy_number):
        """
        Constructor:

        :param pool: The molecule design pool the stock tube sample should
            contain.
        :type pool: :class:`thelma.models.moleculedesign.MoleculeDesignPool`

        :param position_type: The types of the positions in the layouts
            (must be the same for all positions).
        :type position_type: see :class:`MoleculeDesignPoolParameters`

        :param requested_tube_barcode: The barcode of the tube scheduled
            by the :class:`LabIsoBuilder`.
        :type requested_tube_barcode: :class:`basestring`

        :param expected_rack_barcode: The barcode of the rack that the
            scheduled tube is expected in.
        :type expected_rack_barcode: :class:`basestring`

        :param final_position_copy_number: The number of target copies for
            each final plate position (number of ISOs for ISO jobs).
        :type final_position_copy_number: positive :class:`int`
        """
        #: The molecule design pool the stock tube sample should contain.
        self.__pool = pool
        #: The types of the layouts must be the same for all positions.
        self.__position_type = position_type
        #: The barcode of the tube scheduled by the :class:`LabIsoBuilder`.
        self.requested_tube_barcode = requested_tube_barcode
        #: The barcode of the rack that the scheduled tube is expected in.
        self.__exp_rack_barcode = expected_rack_barcode
        #: The target preparation plate position mapped onto plate labels.
        self.__prep_positions = dict()
        #: The target final plate positions.
        self.__final_positions = []
        #: The number of copies for the final positions (default: 1).
        self.__final_position_copy_number = final_position_copy_number

        #: The picked tube candidate for this pool.
        self.tube_candidate = None
        #: The name of the barcoded location the rack is stored at (name and
        #: index).
        self.location = None

    @property
    def pool(self):
        """
        The molecule design pool the stock tube sample should contain
        (:class:`thelma.models.moleculedesign.MoleculeDesignPool`).
        """
        return self.__pool

    @property
    def position_type(self):
        """
        The types of the layouts must be the same for all positions.
        """
        return self.__position_type

    @property
    def expected_rack_barcode(self):
        """
        The barcode of the rack that the scheduled tube is expected in.
        """
        return self.__exp_rack_barcode

    @classmethod
    def from_plate_position(cls, plate_pos, final_position_copy_number):
        """
        Factory method creating a stock tube container from an
        :class:`IsoPlatePosition`.
        """
        kw = dict(pool=plate_pos.molecule_design_pool,
                  position_type=plate_pos.position_type,
                  requested_tube_barcode=plate_pos.stock_tube_barcode,
                  expected_rack_barcode=plate_pos.stock_rack_barcode,
                  final_position_copy_number=final_position_copy_number)
        return cls(**kw)

    @property
    def plate_target_positions(self):
        """
        Returns the target positions mapped onto plate labels. The plate
        label for the final layout is :attr:`LAEBLS.ROLE_FINAL`.
        """
        target_positions = {LABELS.ROLE_FINAL : self.__final_positions}
        target_positions.update(self.__prep_positions)
        return target_positions

    def get_all_target_positions(self):
        """
        Returns all target positions for all plates.
        """
        all_positions = self.__final_positions
        for positions in self.__prep_positions.values():
            all_positions.extend(positions)
        return all_positions

    def get_total_required_volume(self):
        """
        Returns the total volume that needs to be taken from the stock *in ul*.
        """
        volume = 0
        for plate_positions in self.__prep_positions.values():
            for plate_pos in plate_positions:
                volume += plate_pos.get_stock_takeout_volume()
        for plate_positions in self.__final_positions:
            for plate_pos in plate_positions:
                volume += (plate_pos.get_stock_takeout_volume() \
                           * self.__final_position_copy_number)
        return volume

    def get_first_plate(self):
        """
        Returns the label of the first plate. The is the name of the lowest
        preparation plate (if there is any), otherwise the final layout marker
        is returned.
        """
        if len(self.__prep_positions) > 0:
            prep_plates = sorted(self.__prep_positions.keys())
            return prep_plates[0]
        else:
            return LABELS.ROLE_FINAL

    def get_stock_concentration(self):
        """
        Returns the default stock concentration for the pool *in nM*.
        """
        return round(self.__pool.default_stock_concentration \
                     * CONCENTRATION_CONVERSION_FACTOR, 1)

    def add_preparation_position(self, plate_label, plate_pos):
        """
        Registers a target preparation position for this stock tube (used later
        to generated planned worklists).
        """
        add_list_map_element(self.__prep_positions, plate_label, plate_pos)

    def add_final_position(self, plate_pos):
        """
        Registers a target final plate position for this stock tube (used later
        to generated planned worklists).
        """
        self.__final_positions.append(plate_pos)

    def __hash__(self):
        return hash(self.__pool)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__pool == other.pool

    def __str__(self):
        return self.__pool

    def __repr__(self):
        str_format = '<%s pool: %s>'
        params = (self.__class__.__name__, self.__pool)
        return str_format % params
