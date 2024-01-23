from sqlalchemy import Column , BigInteger, String, Numeric
from . import Base 

class BillingReport(Base):
    __tablename__ = "billing_report"

    id = Column(BigInteger, primary_key=True)
    company = Column(String(100), nullable=False)
    cost = Column(Numeric(65, 2), nullable=False)
    dealing_fee = Column(Numeric(65, 2), nullable=False)

class PubSubReport(Base):
    __tablename__ = "pubsub_report"

    id = Column(BigInteger, primary_key=True)
    company = Column(String(100), nullable=False)
    service = Column(String(100), nullable=False)
    cost = Column(Numeric(65, 2), nullable=False)