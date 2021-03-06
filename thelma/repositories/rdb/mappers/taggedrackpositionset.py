"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Tagged rack position set mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.rack import RackPositionSet
from thelma.entities.racklayout import RackLayout
from thelma.entities.tagging import TaggedRackPositionSet


__docformat__ = "epytext"
__all__ = ['create_mapper']


TAGGED_RACK_POSITIONS_TYPE = 'TAGGED_RACK_POSITIONS'


def create_mapper(tagged_mapper, tagged_rack_position_set_tbl):
    "Mapper factory."
    m = mapper(TaggedRackPositionSet, tagged_rack_position_set_tbl,
               inherits=tagged_mapper,
               polymorphic_identity=TAGGED_RACK_POSITIONS_TYPE,
               properties=
                dict(rack_position_set=
                       relationship(
                         RackPositionSet, uselist=False,
#                         lazy='joined'
                         ),
                     layout=
                        relationship(
                          RackLayout,
                          uselist=False,
                          back_populates='tagged_rack_position_sets'),
                     )
               )
    return m


