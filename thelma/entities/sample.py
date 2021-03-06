"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Sample entity classes.
"""
from everest.entities.base import Entity
from everest.entities.utils import slug_from_integer
from thelma.utils import as_utc_time
from thelma.utils import get_utc_time


__docformat__ = 'reStructuredText en'
__all__ = ['SAMPLE_TYPES',
           'Molecule',
           'Sample',
           'StockSample',
           'SampleMolecule',
           'SampleRegistration'
           ]


class SAMPLE_TYPES(object):
    BASIC = 'BASIC'
    STOCK = 'STOCK'


class Molecule(Entity):
    """
    This class represents molecule (solutions).

    :note: Molecules sharing the same molecule design
            (:class:`thelma.entities.moleculedesign.MoleculeDesign`) can be
            listed differently if they are provided by different suppliers
            (:class:`thelma.entities.organization.Organization`).
    """
    #: The date at which the molecule has been inserted into the database.
    insert_date = None
    #: The molecule design
    #: (:class:`thelma.entities.moleculedesign.MoleculeDesign`) for this
    #: molecule.
    molecule_design = None
    #: The supplier of this molecule
    #: (:class:`thelma.entities.organization.Organization`).
    supplier = None
    #: A list of samples (:class:`Sample`) using this molecule.
    samples = None
    #: The supplier's product ID this molecule. This is dynamically
    #: selected by the mapper.
    product_id = None

    def __init__(self, molecule_design, supplier, **kw):
        Entity.__init__(self, **kw)
        self.molecule_design = molecule_design
        self.supplier = supplier
        self.insert_date = get_utc_time()
        self.samples = []

    @property
    def slug(self):
        """
        The slug of molecule objects is derived by the :attr:`id`.
        """
        return slug_from_integer(self.id)

    def __str__(self):
        return str(self.id)

    def __repr__(self):
        str_format = '<%s id: %s, molecule_design: %s, supplier: %s, ' \
                     'product ID: %s, insert_date: %s>'
        params = (self.__class__.__name__, self.id, self.molecule_design,
                  self.supplier, self.product_id, self.insert_date)
        return str_format % params


class Sample(Entity):
    """
    Sample.

    A sample is held by a container and contains one or more sample molecules
    in solution.
    """
    #: The sample volume.
    volume = None
    #: The container (:class:`thelma.entities.container.Container`) holding
    #: the sample.
    container = None
    #: The molecules present in this sample
    #: (:class:`SampleMolecule`) incl.  meta data (e.g. concentration).
    sample_molecules = None
    #: All samples which are aliquots of a `StockSample` reference the ID
    #: of the stock sample's
    #: :class:`thelma.entities.moleculedesign.MoleculeDesignPool`. This
    #: attribute may be `None` for samples that are created by mixing several
    #: stock samples; it will certainly be `None` if the designs of the
    #: sample molecules have not all the same molecule type.
    molecule_design_pool_id = None
    #: Number of freeze/thaw (f/t) cycles this sample has gone through since
    #: it was created. For samples created from other samples, the maximum
    #: f/t cycle count from all source samples is used.
    freeze_thaw_cycles = None
    #: Date time the sample was checked out of the stock. `None` if it is
    #: currently checked in.
    checkout_date = None

    def __init__(self, volume, container, **kw):
        Entity.__init__(self, **kw)
        self.volume = volume
        self.container = container
        self.sample_type = SAMPLE_TYPES.BASIC
        self.__thaw_time = None

    @property
    def thaw_time(self):
        if self.__thaw_time is None:
            self.__thaw_time = \
                min([sm.molecule.molecule_design.molecule_type.thaw_time
                     for sm in self.sample_molecules])
        return self.__thaw_time

    def make_sample_molecule(self, molecule, concentration, **kw):
        tt = molecule.molecule_design.molecule_type.thaw_time
        if self.__thaw_time is None or tt < self.__thaw_time:
            self.__thaw_time = tt
        return SampleMolecule(molecule, concentration, sample=self, **kw)

    def convert_to_stock_sample(self):
        """
        Converts this instance into a stock sample by setting all the
        required attributes. The object class is ''not'' changed.
        """
        mols = [sm.molecule for sm in self.sample_molecules]
        if len(mols) == 0:
            raise ValueError('Stock samples must have at least one sample '
                             'molecule.')
        if len(set([(mol.supplier, mol.molecule_design.molecule_type,
                     self.sample_molecules[idx].concentration)
                    for (idx, mol) in enumerate(mols)])) > 1:
            raise ValueError('All molecule designs in a stock sample must '
                             'have the same supplier, the same molecule type '
                             'and the same concentration.')
        from thelma.entities.moleculedesign import MoleculeDesignPool
        mdp = MoleculeDesignPool.create_from_data(
                            dict(molecule_designs=set([mol.molecule_design
                                                       for mol in mols])))
        # Setting attributes outside __init__ pylint: disable=W0201
        concentration = 0
        for sm in self.sample_molecules:
            concentration += sm.concentration
        concentration = round(concentration, 10) # one decimal place if in nM
        self.molecule_design_pool = mdp
        self.supplier = mols[0].supplier
        self.molecule_type = mols[0].molecule_design.molecule_type
        self.concentration = concentration
        self.sample_type = SAMPLE_TYPES.STOCK
        self.__class__ = StockSample
        # pylint: enable=W0201

    @property
    def is_checked_out(self):
        return not self.checkout_date is None

    def check_in(self):
        """
        Checks this sample into a freezer.

        Requires the `checkout_date` attribute to be set so that we can
        determine if a freeze/thaw cycle increment is in order.

        :raises RuntimeError: If the `checkout_date` attribute is `None`.
        """
        checkout_date = self.checkout_date
        if checkout_date is None:
            raise RuntimeError('Trying to check in a sample that has not '
                               'been checked out.')
        if checkout_date.tzinfo is None:
            checkout_date = as_utc_time(self.checkout_date)
        checkout_secs = abs(get_utc_time() - checkout_date).seconds
        if checkout_secs > self.thaw_time:
            if self.freeze_thaw_cycles is None:
                self.freeze_thaw_cycles = 1
            else:
                self.freeze_thaw_cycles += 1
        self.checkout_date = None

    def check_out(self):
        """
        Checks this sample out of the freezer it is currently in.

        :raises RuntimeError: If the `checkout_date` attribute is not `None`.
        """
        if not self.checkout_date is None:
            raise RuntimeError('Trying to check out a sample that has not '
                               'been checked in.')
        self.checkout_date = get_utc_time()

    def __repr__(self):
        str_format = '<%s id: %s, container: %s, volume: %s>'
        params = (self.__class__.__name__, self.id, self.container,
                  self.volume)
        return str_format % params


class StockSample(Sample):
    """
    Stock sample.

    A stock sample is a sample that satisfies the following constraints:
     * All sample molecules have the same supplier;
     * All sample molecules have the same molecule type;
     * All sample molecules have the same concentration.

    The molecule designs of all molecules in a stock sample are kept in a
    :class:`thelma.entities.moleculedesign.MoleculeDesignPool`.
    """
    #: The supplier for all sample molecules.
    supplier = None
    #: The molecule type of all sample molecules.
    molecule_type = None
    #: The combined concentration of all sample molecules.
    concentration = None
    #: The registration event for this stock sample.
    registration = None
    #: The molecule design pool for the sample molecules in this stock
    #: sample.
    molecule_design_pool = None
    #: The product ID for the molecule design pool / supplier combination
    #: in this stock sample. This is dynamically selected by the mapper.
    product_id = None

    def __init__(self, volume, container, molecule_design_pool, supplier,
                 molecule_type, concentration, **kw):
        Sample.__init__(self, volume, container, **kw)
        self.sample_type = SAMPLE_TYPES.STOCK
        if molecule_design_pool.molecule_type != molecule_type:
            raise ValueError('The molecule types of molecule design pool '
                             'and stock sample differ.')
        self.molecule_design_pool = molecule_design_pool
        self.molecule_type = molecule_type
        self.supplier = supplier
        self.concentration = concentration
        # Create the sample molecules for this stock sample. By definition,
        # they all have the same supplier and same concentration (which is
        # determined by dividing the total concentration by the number of
        # sample molecules).
        sm_mol_conc = \
            concentration / len(molecule_design_pool.molecule_designs)
        for molecule_design in molecule_design_pool.molecule_designs:
            mol = Molecule(molecule_design, supplier)
            self.make_sample_molecule(mol, sm_mol_conc)
        self.registration = None

    @property
    def thaw_time(self):
        return self.molecule_type.thaw_time

    def register(self):
        self.registration = SampleRegistration(self, self.volume)
        self.freeze_thaw_cycles = 0


class SampleMolecule(Entity):
    """
    This class represents a molecule in a particular sample. It also stores
    the meta data for it.
    """
    #: The samples (:class:`Sample`) containing this molecule.
    sample = None
    #: The molecule regarded by this object.
    molecule = None
    #: The concentration of the :attr:`molecule` in the :attr:`sample`
    #: in [*moles per liter*].
    concentration = None
    #: The number of freeze thaw samples for the :attr:`molecule`.
    freeze_thaw_cycles = None
    #: The date of the last check out.
    checkout_date = None

    def __init__(self, molecule, concentration, sample=None, **kw):
        Entity.__init__(self, **kw)
        self.molecule = molecule
        self.concentration = concentration
        self.sample = sample
        self.freeze_thaw_cycles = 0

    def __eq__(self, other):
        """
        Equality is based on the sample and molecule attributes.
        """
        return (isinstance(other, SampleMolecule) and
                self.sample == other.sample and
                self.molecule == other.molecule)

    def __str__(self):
        return str((self.sample, self.molecule))

    def __repr__(self):
        str_format = '<%s sample: %s, molecule: %s, concentration: %s, ' \
                     'freeze_thaw_cycles: %s, checkout_date: %s>'
        params = (self.__class__.__name__, self.sample, self.molecule,
                  self.concentration, self.freeze_thaw_cycles,
                  self.checkout_date)
        return str_format % params


class SampleRegistration(Entity):
    """
    Represents a sample registration event.
    """
    #: The (stock) sample which was registered.
    sample = None
    #: The initial sample volume at registration time.
    volume = None
    #: Time stamp.
    time_stamp = None

    def __init__(self, sample, volume, time_stamp=None, **kw):
        Entity.__init__(self, **kw)
        self.sample = sample
        self.volume = volume
        if time_stamp is None:
            time_stamp = get_utc_time()
        self.time_stamp = time_stamp
