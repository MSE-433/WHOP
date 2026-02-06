from pydantic import BaseModel


class CostEntry(BaseModel):
    financial: int = 0
    quality: int = 0


class CostConstants(BaseModel):
    """Cost rates per the FNER scoring worksheet."""

    # ER-specific
    er_diversion_financial: int = 5000
    er_diversion_quality: int = 200
    er_waiting_financial: int = 150
    er_waiting_quality: int = 20

    # All departments
    extra_staff_financial: int = 40
    extra_staff_quality: int = 5

    # Surgery / CC / Step Down
    arrivals_waiting_financial: int = 3750
    arrivals_waiting_quality: int = 20
    requests_waiting_financial: int = 0
    requests_waiting_quality: int = 20


# Singleton
COST_CONSTANTS = CostConstants()
