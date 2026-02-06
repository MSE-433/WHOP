"""Test rule enforcement (validator)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from models.enums import DepartmentId
from models.actions import (
    ArrivalsAction, AdmitDecision, AcceptTransferDecision,
    ExitsAction, ExitRouting,
    StaffingAction, StaffTransfer,
)
from engine.validator import (
    validate_arrivals, validate_exits, validate_staffing, ValidationError,
)
from data.starting_state import create_starting_state


@pytest.fixture
def game():
    return create_starting_state("test")


class TestArrivalsValidation:

    def test_admit_more_than_waiting_raises(self, game):
        game.departments[DepartmentId.ER].arrivals_waiting = 2
        action = ArrivalsAction(admissions=[
            AdmitDecision(department=DepartmentId.ER, admit_count=5)
        ])
        with pytest.raises(ValidationError, match="only 2 waiting"):
            validate_arrivals(game, action)

    def test_admit_more_than_idle_staff_raises(self, game):
        game.departments[DepartmentId.ER].arrivals_waiting = 10
        # ER starts with 18 core, 16 busy = 2 idle
        action = ArrivalsAction(admissions=[
            AdmitDecision(department=DepartmentId.ER, admit_count=5)
        ])
        with pytest.raises(ValidationError, match="idle staff"):
            validate_arrivals(game, action)

    def test_admit_within_limits_passes(self, game):
        game.departments[DepartmentId.ER].arrivals_waiting = 2
        # ER: 18 core, 16 busy = 2 idle
        action = ArrivalsAction(admissions=[
            AdmitDecision(department=DepartmentId.ER, admit_count=2)
        ])
        validate_arrivals(game, action)  # Should not raise

    def test_admit_exceeds_bed_cap_surgery_raises(self, game):
        surg = game.departments[DepartmentId.SURGERY]
        surg.patients_in_beds = 9  # at cap
        surg.staff.core_busy = 4
        surg.staff.extra_total = 5
        surg.arrivals_waiting = 3
        action = ArrivalsAction(admissions=[
            AdmitDecision(department=DepartmentId.SURGERY, admit_count=1)
        ])
        with pytest.raises(ValidationError, match="beds available"):
            validate_arrivals(game, action)

    def test_negative_admit_raises(self, game):
        action = ArrivalsAction(admissions=[
            AdmitDecision(department=DepartmentId.ER, admit_count=-1)
        ])
        with pytest.raises(ValidationError, match="negative"):
            validate_arrivals(game, action)


class TestExitsValidation:

    def test_invalid_transfer_route_raises(self, game):
        # ER -> ER is not a valid route
        action = ExitsAction(routings=[
            ExitRouting(
                from_dept=DepartmentId.ER,
                transfers={DepartmentId.ER: 1}
            )
        ])
        with pytest.raises(ValidationError, match="not allowed"):
            validate_exits(game, action)

    def test_valid_transfer_route_passes(self, game):
        # ER -> Surgery is valid
        action = ExitsAction(routings=[
            ExitRouting(
                from_dept=DepartmentId.ER,
                transfers={DepartmentId.SURGERY: 1}
            )
        ])
        validate_exits(game, action)  # Should not raise


class TestStaffingValidation:

    def test_return_more_extra_than_available_raises(self, game):
        # No extra staff at start
        action = StaffingAction(return_extra={DepartmentId.ER: 5})
        with pytest.raises(ValidationError, match="idle extra staff"):
            validate_staffing(game, action)

    def test_transfer_more_than_idle_raises(self, game):
        # ER: 2 idle (18 core - 16 busy)
        action = StaffingAction(transfers=[
            StaffTransfer(from_dept=DepartmentId.ER, to_dept=DepartmentId.SURGERY, count=5)
        ])
        with pytest.raises(ValidationError, match="idle"):
            validate_staffing(game, action)

    def test_negative_extra_staff_raises(self, game):
        action = StaffingAction(extra_staff={DepartmentId.ER: -1})
        with pytest.raises(ValidationError, match="negative"):
            validate_staffing(game, action)
