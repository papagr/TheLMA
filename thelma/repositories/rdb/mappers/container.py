"""
Container mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import mapper
from thelma.entities.container import CONTAINER_TYPES
from thelma.entities.container import Container
from thelma.entities.container import ContainerSpecs
from thelma.entities.status import ItemStatus


__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(container_tbl):
    "Mapper factory."
    m = mapper(Container, container_tbl,
           id_attribute='container_id',
           properties=
            dict(specs=relationship(ContainerSpecs, uselist=False),
                 #empty=True or False if it has no sample or volume is 0
                 status=relationship(ItemStatus, uselist=False),
                 ),
            polymorphic_on=container_tbl.c.container_type,
            polymorphic_identity=CONTAINER_TYPES.CONTAINER
            )
    return m
