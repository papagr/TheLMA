"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Rack position mapper.
"""
from sqlalchemy import func

from everest.repositories.rdb.utils import mapper
from thelma.entities.rack import RackPosition


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(rack_position_tbl):
    "Mapper factory."
    m = mapper(RackPosition, rack_position_tbl,
               id_attribute='rack_position_id',
               slug_expression=lambda cls: func.lower(cls._label), # pylint: disable=W0212
               properties=
                 dict(_label=rack_position_tbl.c.label,
                      _row_index=rack_position_tbl.c.row_index,
                      _column_index=rack_position_tbl.c.column_index
                      ),
               )
    return m

