"""Test card sequence data integrity."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.card_sequences import (
    ER_WALKIN, ER_AMBULANCE, ER_EXITS,
    SURGERY_ARRIVALS, SURGERY_EXITS,
    CC_ARRIVALS, CC_EXITS,
    SD_ARRIVALS, SD_EXITS,
    get_arrivals, get_exits,
)
from models.enums import DepartmentId


class TestCardSequenceLengths:
    """All sequences must have exactly 24 values (one per round)."""

    def test_er_walkin_length(self):
        assert len(ER_WALKIN) == 24

    def test_er_ambulance_length(self):
        assert len(ER_AMBULANCE) == 24

    def test_er_exits_length(self):
        assert len(ER_EXITS) == 24

    def test_surgery_arrivals_length(self):
        assert len(SURGERY_ARRIVALS) == 24

    def test_surgery_exits_length(self):
        assert len(SURGERY_EXITS) == 24

    def test_cc_arrivals_length(self):
        assert len(CC_ARRIVALS) == 24

    def test_cc_exits_length(self):
        assert len(CC_EXITS) == 24

    def test_sd_arrivals_length(self):
        assert len(SD_ARRIVALS) == 24

    def test_sd_exits_length(self):
        assert len(SD_EXITS) == 24


class TestCardSequenceSums:
    """Verify sums match known totals from the FNER data sheet."""

    def test_er_walkin_sum(self):
        assert sum(ER_WALKIN) == 76

    def test_er_ambulance_sum(self):
        assert sum(ER_AMBULANCE) == 28

    def test_er_exits_sum(self):
        assert sum(ER_EXITS) == 40

    def test_surgery_arrivals_sum(self):
        assert sum(SURGERY_ARRIVALS) == 8

    def test_surgery_exits_sum(self):
        assert sum(SURGERY_EXITS) == 3

    def test_cc_arrivals_sum(self):
        assert sum(CC_ARRIVALS) == 4

    def test_cc_exits_sum(self):
        assert sum(CC_EXITS) == 4

    def test_sd_exits_sum(self):
        assert sum(SD_EXITS) == 20


class TestGetterFunctions:
    """Test the convenience getter functions."""

    def test_get_arrivals_er_round1(self):
        # ER round 1: walkin=2 + ambulance=0 = 2
        assert get_arrivals(DepartmentId.ER, 1) == 2

    def test_get_arrivals_er_round4(self):
        # ER round 4: walkin=6 + ambulance=2 = 8
        assert get_arrivals(DepartmentId.ER, 4) == 8

    def test_get_exits_er_round1(self):
        assert get_exits(DepartmentId.ER, 1) == 5

    def test_get_arrivals_surgery_round1(self):
        assert get_arrivals(DepartmentId.SURGERY, 1) == 3

    def test_get_exits_surgery_round3(self):
        assert get_exits(DepartmentId.SURGERY, 3) == 1

    def test_all_values_non_negative(self):
        for seq in [ER_WALKIN, ER_AMBULANCE, ER_EXITS,
                    SURGERY_ARRIVALS, SURGERY_EXITS,
                    CC_ARRIVALS, CC_EXITS,
                    SD_ARRIVALS, SD_EXITS]:
            assert all(v >= 0 for v in seq)
