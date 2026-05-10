"""Finance data models using Beanie ODM for MongoDB."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class Earning(BaseModel):
    """Earning component in a payslip."""
    
    type: str = Field(..., description="Type of earning (e.g., 'Basic Salary', 'HRA')")
    amount: Decimal = Field(..., description="Earning amount")
    arrear_amount: Optional[Decimal] = Field(None, description="Arrear amount if any")


class Deduction(BaseModel):
    """Deduction component in a payslip."""
    
    type: str = Field(..., description="Type of deduction (e.g., 'PF', 'TDS')")
    amount: Decimal = Field(..., description="Deduction amount")


class Employer(Document):
    """Employer entity model."""
    
    name: Indexed(str) = Field(..., description="Employer name")
    active: bool = Field(True, description="Whether employer is active")
    
    class Settings:
        name = "employers"


class User(Document):
    """User entity model."""
    
    username: Indexed(str, unique=True) = Field(..., description="Unique username")
    employer_ids: List[str] = Field(default_factory=list, description="List of employer IDs")
    
    class Settings:
        name = "users"


class Payslip(Document):
    """Payslip entity model."""
    
    user_id: Indexed(str) = Field(..., description="User who owns this payslip")
    employer_id: Indexed(str) = Field(..., description="Employer for this payslip")
    bank_name: str = Field(..., description="Bank name")
    bank_account_no: str = Field(..., description="Bank account number")
    
    # Period information
    month: datetime = Field(..., description="Month and year of payslip")
    number_of_days: int = Field(..., description="Number of days in period")
    lop: int = Field(default=0, description="Leave of Pay days")
    lopr: int = Field(default=0, description="Leave of Pay Recovery days")
    
    # Financial components
    earnings: List[Earning] = Field(default_factory=list, description="List of earnings")
    deductions: List[Deduction] = Field(default_factory=list, description="List of deductions")
    
    class Settings:
        name = "payslips"
