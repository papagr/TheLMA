"""
This file is part of the TheLMA (THe Laboratory Management Application) project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Experiment rack job table.
"""
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Table


__docformat__ = 'reStructuredText en'
__all__ = ['create_table']


def create_table(metadata, job_tbl, experiment_rack_tbl):
    "Table factory."
    #FIXME: check update and delete constraints #pylint: disable=W0511
    tbl = Table('experiment_rack_job', metadata,
                Column('experiment_rack_id', Integer,
                       ForeignKey(experiment_rack_tbl.c.experiment_rack_id),
                       nullable=False),
                Column('job_id', Integer,
                       ForeignKey(job_tbl.c.job_id), nullable=False)
                )
    return tbl
