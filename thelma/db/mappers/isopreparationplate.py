"""
ISO preparation plate mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.iso import ISO_PLATE_TYPES
from thelma.models.iso import Iso
from thelma.models.iso import IsoPreparationPlate
from thelma.models.racklayout import RackLayout

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(iso_plate_mapper, iso_preparation_plate_tbl):
    "Mapper factory."
    m = mapper(IsoPreparationPlate, iso_preparation_plate_tbl,
               inherits=iso_plate_mapper,
               properties=dict(
                    iso=relationship(Iso, uselist=False,
                        back_populates='iso_preparation_plates'),
                    rack_layout=relationship(RackLayout, uselist=False,
                        cascade='all,delete,delete-orphan',
                        single_parent=True)
                    ),
               polymorphic_identity=ISO_PLATE_TYPES.PREPARATION,
               )
    return m
