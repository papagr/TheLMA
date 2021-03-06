"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule design table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, molecule_type_tbl):
    "Table factory."
    tbl = Table('molecule_design', metadata,
        Column('molecule_design_id', Integer, primary_key=True),
        Column('molecule_type', String(10),
               ForeignKey(molecule_type_tbl.c.molecule_type_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               key='molecule_type_id', nullable=False, index=True),
        Column('structure_hash', String, nullable=False, unique=True),
        )
    return tbl
