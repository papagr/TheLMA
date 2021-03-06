"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

ISO mapper.
"""
from sqlalchemy.orm import relationship

from everest.repositories.rdb.utils import as_slug_expression
from everest.repositories.rdb.utils import mapper
from thelma.entities.iso import ISO_TYPES
from thelma.entities.iso import Iso
from thelma.entities.iso import IsoAliquotPlate
from thelma.entities.iso import IsoPreparationPlate
from thelma.entities.iso import IsoRequest
from thelma.entities.iso import IsoSectorStockRack
from thelma.entities.iso import IsoStockRack
from thelma.entities.job import IsoJob
from thelma.entities.moleculedesign import MoleculeDesignPoolSet
from thelma.entities.racklayout import RackLayout


__docformat__ = "reStructuredText en"
__all__ = ['create_mapper']


def create_mapper(iso_tbl, job_tbl, iso_job_member_tbl, iso_pool_set_tbl):
    "Mapper factory."
    j = job_tbl
    ijm = iso_job_member_tbl
    m = mapper(Iso, iso_tbl,
        id_attribute='iso_id',
        slug_expression=lambda cls: as_slug_expression(cls.label),
        properties=
            dict(iso_request=relationship(IsoRequest,
                                         uselist=False,
                                         back_populates='isos'),
                 molecule_design_pool_set=
                        relationship(MoleculeDesignPoolSet,
                                     uselist=False,
                                     secondary=iso_pool_set_tbl),
                 rack_layout=relationship(RackLayout, uselist=False,
                                          cascade='all,delete,delete-orphan',
                                          single_parent=True),
                 iso_stock_racks=relationship(IsoStockRack,
                             back_populates='iso',
                             cascade='all,delete,delete-orphan'),
                 iso_sector_stock_racks=relationship(IsoSectorStockRack,
                             back_populates='iso',
                             cascade='all,delete,delete-orphan'),
                 iso_aliquot_plates=relationship(IsoAliquotPlate,
                              back_populates='iso',
                              cascade='all,delete-orphan'),
                 iso_preparation_plates=relationship(IsoPreparationPlate,
                              back_populates='iso'),
                 iso_job=relationship(IsoJob, uselist=False,
                             primaryjoin=(iso_tbl.c.iso_id == ijm.c.iso_id),
                             secondaryjoin=(ijm.c.job_id == j.c.job_id),
                             secondary=ijm,
                             back_populates='isos',
                             cascade='all'),
                 ),
               polymorphic_on=iso_tbl.c.iso_type,
               polymorphic_identity=ISO_TYPES.BASE,
               )
    return m
