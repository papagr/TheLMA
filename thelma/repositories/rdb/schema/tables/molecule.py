"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Molecule table.
"""
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, molecule_design_tbl, organization_tbl):
    "Table factory."
    tbl = Table('molecule', metadata,
        Column('molecule_id', Integer, primary_key=True),
        Column('insert_date', DateTime(timezone=True), default=datetime.now),
        Column('molecule_design_id', Integer,
               ForeignKey(molecule_design_tbl.c.molecule_design_id,
                          onupdate='CASCADE', ondelete='RESTRICT'),
               nullable=False, index=True),
        Column('supplier_id', Integer,
               ForeignKey(organization_tbl.c.organization_id),
               nullable=False),
        )
    return tbl
