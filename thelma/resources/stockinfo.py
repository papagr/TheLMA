"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Stock info resource.
"""
from everest.constants import CARDINALITIES
from everest.querying.specifications import AscendingOrderSpecification
from everest.resources.base import Collection
from everest.resources.base import Member
from everest.resources.descriptors import attribute_alias
from everest.resources.descriptors import collection_attribute
from everest.resources.descriptors import member_attribute
from everest.resources.descriptors import terminal_attribute
from thelma.interfaces import IGene
from thelma.interfaces import IMoleculeDesignPool
from thelma.interfaces import IMoleculeType
from thelma.resources.base import RELATION_BASE_URL


__docformat__ = 'reStructuredText en'
__all__ = ['StockInfoCollection',
           'StockInfoMember',
           ]


class StockInfoMember(Member):
    relation = "%s/stock-info" % RELATION_BASE_URL
    title = attribute_alias('id')
    id = terminal_attribute(str, 'id') # stock info IDs are *strings*.
    # FIXME: This should be called molecule_design_pool_id in the entity
    molecule_design_pool_id = terminal_attribute(int,
                                                'molecule_design_set_id')
    total_tubes = terminal_attribute(int, 'total_tubes')
    total_volume = terminal_attribute(float, 'total_volume')
    maximum_volume = terminal_attribute(float, 'maximum_volume')
    minimum_volume = terminal_attribute(float, 'minimum_volume')
    concentration = terminal_attribute(float, 'concentration')
    molecule_type = member_attribute(IMoleculeType, 'molecule_type')
    molecule_design_pool = member_attribute(IMoleculeDesignPool,
                                            'molecule_design_pool')
    genes = collection_attribute(IGene, 'genes',
                                 cardinality=CARDINALITIES.MANYTOMANY)


class StockInfoCollection(Collection):
    title = 'Stock Info'
    root_name = 'stock-info'
    description = 'Stock related information'
    default_order = AscendingOrderSpecification('molecule_design_pool.id')
