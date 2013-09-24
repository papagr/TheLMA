"""
Executed worklist mapper.
"""
from everest.repositories.rdb.utils import mapper
from sqlalchemy.orm import relationship
from thelma.models.liquidtransfer import ExecutedLiquidTransfer
from thelma.models.liquidtransfer import ExecutedWorklist
from thelma.models.liquidtransfer import PlannedWorklist

__docformat__ = 'reStructuredText en'
__all__ = ['create_mapper']


def create_mapper(executed_worklist_tbl, executed_liquid_transfer_tbl,
                  executed_worklist_member_tbl):
    "Mapper factory."
    ew = executed_worklist_tbl
    ewm = executed_worklist_member_tbl
    elt = executed_liquid_transfer_tbl
    m = mapper(ExecutedWorklist, executed_worklist_tbl,
               id_attribute='executed_worklist_id',
               properties=dict(
                    planned_worklist=relationship(PlannedWorklist,
                            uselist=False,
                            back_populates='executed_worklists',
                            cascade='all,delete-orphan'),
                    executed_transfers=relationship(ExecutedLiquidTransfer,
                            uselist=True,
                            primaryjoin=(ew.c.executed_worklist_id == \
                                         ewm.c.executed_worklist_id),
                            secondaryjoin=(ewm.c.executed_liquid_transfer_id == \
                                           elt.c.executed_liquid_transfer_id),
                            secondary=ewm),
                    )
            )
    return m
