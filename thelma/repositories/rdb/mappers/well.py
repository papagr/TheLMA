"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Well mapper.
"""
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from thelma.entities.container import CONTAINER_TYPES
from thelma.entities.container import Well
from thelma.entities.rack import Plate
from thelma.entities.rack import RackPosition


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(container_mapper, well_tbl):
    "Mapper factory."
    m = mapper(Well, well_tbl,
               inherits=container_mapper,
               properties=
                 dict(rack=relationship(Plate, uselist=False),
                      position=relationship(RackPosition, uselist=False),
#                    sample=relationship(Sample, uselist=False,
#                                        back_populates='container',
#                                        ),
                      ),
               polymorphic_identity=CONTAINER_TYPES.WELL)
    # FIXME: need a slug here # pylint:disable=W0511
    return m
