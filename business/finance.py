from typing import Any, Dict, List, Optional
from common_utils.logger import get_logger

logger = get_logger(__name__)

class FinanceBusinessBase:
    """Base class for finance business logic."""
    def __init__(self, service):
        self.service = service

class EmployerBusiness(FinanceBusinessBase):
    """Business logic for Employer service."""
    
    async def build_employer_lookups(self, entity: Any) -> Dict[str, Any]:
        """Build optimized lookup structures for employer."""
        # Example implementation
        return {
            "lookup_key": f"employer:{entity.name.lower()}",
            "is_active": entity.active
        }

class UserBusiness(FinanceBusinessBase):
    """Business logic for User service."""
    
    async def build_user_lookups(self, entity: Any) -> Dict[str, Any]:
        """Build optimized lookup structures for user."""
        return {
            "username_key": entity.username.lower(),
            "employer_count": len(entity.employer_ids)
        }

class PayslipBusiness(FinanceBusinessBase):
    """Business logic for Payslip service."""
    
    async def build_payslip_lookups(self, entity: Any) -> Dict[str, Any]:
        """Build optimized lookup structures for payslip."""
        return {
            "user_employer_key": f"{entity.user_id}:{entity.employer_id}",
            "period": entity.month.strftime("%Y-%m")
        }
