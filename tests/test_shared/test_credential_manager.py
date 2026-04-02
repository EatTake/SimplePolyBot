import time
from unittest.mock import patch

import pytest
from datetime import datetime, timezone, timedelta

from shared.credential_manager import CredentialManager


class TestCredentialManagerInit:
    def test_default_values(self):
        cm = CredentialManager()
        assert cm.rotation_interval_days == 90
        assert isinstance(cm.last_rotation, datetime)
        assert cm.rotation_history == []
        assert cm._current_creds_summary is None

    def test_custom_rotation_interval(self):
        cm = CredentialManager(rotation_interval_days=30)
        assert cm.rotation_interval_days == 30

    def test_last_rotation_is_utc_aware(self):
        cm = CredentialManager()
        assert cm.last_rotation.tzinfo is not None


class TestShouldRotate:
    def test_not_expired_returns_false(self):
        cm = CredentialManager(rotation_interval_days=90)
        assert cm.should_rotate() is False

    def test_expired_returns_true(self, freezer):
        cm = CredentialManager(rotation_interval_days=1)
        freezer.tick(timedelta(days=2))
        assert cm.should_rotate() is True

    def test_exactly_at_threshold_returns_true(self, freezer):
        cm = CredentialManager(rotation_interval_days=1)
        freezer.tick(timedelta(days=1))
        assert cm.should_rotate() is True

    def test_rotation_resets_timer(self, freezer):
        cm = CredentialManager(rotation_interval_days=1)
        freezer.tick(timedelta(days=2))
        assert cm.should_rotate() is True
        cm.rotate_credentials()
        assert cm.should_rotate() is False


class TestRotateCredentials:
    def test_updates_timestamp(self, freezer):
        cm = CredentialManager()
        original_time = cm.last_rotation
        freezer.tick(timedelta(seconds=10))
        result = cm.rotate_credentials()

        assert cm.last_rotation != original_time
        assert result["rotated_at"] == cm.last_rotation.isoformat()

    def test_without_new_creds_records_success_status(self):
        cm = CredentialManager()
        result = cm.rotate_credentials()

        assert result["status"] == "success"
        history = cm.get_history()
        assert len(history) == 1
        assert history[0]["status"] == "success"

    def test_with_new_creds_records_manual_status(self):
        cm = CredentialManager()
        new_creds = {"api_key": "new_key", "secret": "new_secret"}
        result = cm.rotate_credentials(new_creds)

        assert result["status"] == "manual"
        history = cm.get_history()
        assert history[0]["status"] == "manual"
        assert history[0]["new_creds_summary"] == "keys=['api_key', 'secret']"

    def test_returns_correct_days_until_next_rotation(self):
        cm = CredentialManager(rotation_interval_days=60)
        result = cm.rotate_credentials()
        assert result["days_until_next_rotation"] == 60

    def test_previous_creds_summary_is_none_on_first_rotation(self):
        cm = CredentialManager()
        cm.rotate_credentials()
        history = cm.get_history()
        assert history[0]["previous_creds_summary"] is None

    def test_previous_creds_summary_captured_after_first_rotation(self):
        cm = CredentialManager()
        cm.rotate_credentials({"key": "v1"})
        cm.rotate_credentials({"key": "v2"})
        history = cm.get_history()

        assert history[1]["previous_creds_summary"] == "keys=['key']"


class TestRotationHistory:
    def test_empty_initially(self):
        cm = CredentialManager()
        assert cm.get_history() == []

    def test_accumulates_rotations(self):
        cm = CredentialManager()
        cm.rotate_credentials()
        cm.rotate_credentials({"k": "v"})
        cm.rotate_credentials()

        history = cm.get_history()
        assert len(history) == 3

    def test_history_entries_have_required_keys(self):
        cm = CredentialManager()
        cm.rotate_credentials({"a": "b"})

        entry = cm.get_history()[0]
        required_keys = {"timestamp", "previous_creds_summary", "new_creds_summary", "status"}
        assert set(entry.keys()) == required_keys

    def test_history_entries_are_in_chronological_order(self, freezer):
        cm = CredentialManager()
        cm.rotate_credentials()
        freezer.tick(timedelta(hours=1))
        cm.rotate_credentials()
        freezer.tick(timedelta(hours=1))
        cm.rotate_credentials()

        history = cm.get_history()
        for i in range(len(history) - 1):
            t1 = datetime.fromisoformat(history[i]["timestamp"])
            t2 = datetime.fromisoformat(history[i + 1]["timestamp"])
            assert t1 < t2

    def test_get_history_returns_copy_not_reference(self):
        cm = CredentialManager()
        cm.rotate_credentials()
        history1 = cm.get_history()
        history2 = cm.get_history()
        assert history1 is not history2
        assert history1 == history2


class TestGetRotationInfo:
    def test_info_completeness(self):
        cm = CredentialManager(rotation_interval_days=45)
        info = cm.get_rotation_info()

        expected_keys = {
            "last_rotation",
            "days_since_last_rotation",
            "should_rotate",
            "rotation_interval_days",
            "total_rotations",
        }
        assert set(info.keys()) == expected_keys

    def test_total_rotations_matches_history_length(self):
        cm = CredentialManager()
        info = cm.get_rotation_info()
        assert info["total_rotations"] == 0

        cm.rotate_credentials()
        info = cm.get_rotation_info()
        assert info["total_rotations"] == 1

        cm.rotate_credentials()
        info = cm.get_rotation_info()
        assert info["total_rotations"] == 2

    def test_should_rotate_consistent_with_method(self, freezer):
        cm = CredentialManager(rotation_interval_days=1)
        info = cm.get_rotation_info()
        assert info["should_rotate"] == cm.should_rotate()

        freezer.tick(timedelta(days=2))
        info = cm.get_rotation_info()
        assert info["should_rotate"] == cm.should_rotate()
        assert info["should_rotate"] is True

    def test_days_since_last_rotation_accuracy(self, freezer):
        cm = CredentialManager()
        freezer.tick(timedelta(hours=36))
        info = cm.get_rotation_info()

        assert abs(info["days_since_last_rotation"] - 1.5) < 0.01

    def test_rotation_interval_days_reflects_config(self):
        cm = CredentialManager(rotation_interval_days=120)
        info = cm.get_rotation_info()
        assert info["rotation_interval_days"] == 120


class TestManualTriggerRotation:
    def test_manual_rotation_resets_should_rotate(self, freezer):
        cm = CredentialManager(rotation_interval_days=1)
        freezer.tick(timedelta(days=5))
        assert cm.should_rotate() is True

        cm.rotate_credentials(new_creds={"api_key": "fresh_key"})
        assert cm.should_rotate() is False

    def test_manual_rotation_increments_total_count(self):
        cm = CredentialManager()
        cm.rotate_credentials(new_creds={"x": "y"})
        assert cm.get_rotation_info()["total_rotations"] == 1

    def test_multiple_manual_rotations_tracked(self):
        cm = CredentialManager()
        for i in range(5):
            cm.rotate_credentials(new_creds={"key": f"v{i}"})

        assert len(cm.get_history()) == 5
        for entry in cm.get_history():
            assert entry["status"] == "manual"


@pytest.fixture
def freezer():
    class _Freezer:
        def __init__(self):
            self._offset = timedelta(0)

        def tick(self, delta: timedelta):
            self._offset += delta

        @property
        def offset(self):
            return self._offset

    f = _Freezer()

    original_now = datetime.now

    def mock_now(tz=None):
        base = original_now(timezone.utc) if tz is None else original_now(tz)
        return base + f.offset

    with patch("shared.credential_manager.datetime") as mock_dt:
        mock_dt.now.side_effect = mock_now
        mock_dt.side_effect = lambda *args, **kw: original_now(*args, **kw)
        yield f
