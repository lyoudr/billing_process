from pydantic import BaseModel 
from typing import Optional
from decimal import Decimal
class BillingReportModel(BaseModel):
    company: str 
    total_cost: Decimal 
    discounted_cost: Decimal 
    tech_fee: Decimal 