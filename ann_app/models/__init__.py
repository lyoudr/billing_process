from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base
import os
import sys



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))


# The naming convention refers: https://alembic.sqlalchemy.org/en/latest/naming.html#integration-of-naming-conventions-into-operations-autogenerate
meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)
Base = declarative_base(metadata=meta)

from .billing import BillingReport, PubSubReport
