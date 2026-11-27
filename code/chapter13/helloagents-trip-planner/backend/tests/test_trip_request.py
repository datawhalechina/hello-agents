"""Request-boundary tests that need no LLM or map credentials."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pydantic import ValidationError
from app.models.schemas import TripRequest


class TestTripRequestDates(unittest.TestCase):
    def request(self, **overrides):
        values = dict(city="北京", start_date="2026-01-01", end_date="2026-01-03",
                      travel_days=3, transportation="公共交通", accommodation="酒店")
        return TripRequest(**dict(values, **overrides))

    def test_valid_calendar_dates_remain_strings(self):
        for value in ("2024-02-29", "2026-12-31", "0001-01-01"):
            with self.subTest(value=value):
                request = self.request(start_date=value, end_date=value)
                self.assertEqual(request.start_date, value)
                self.assertEqual(request.model_dump()["end_date"], value)
                self.assertIsInstance(request.start_date, str)

    def test_invalid_dates_are_rejected_for_both_fields(self):
        invalid = ("not-a-date", "2026-02-29", "2026-02-30", "2026-04-31",
                   "2026-13-01", "0000-01-01", "20260101", "2026-1-01",
                   "2026-01-1", "2026-W01-1", "2026-01-01T00:00:00", " 2026-01-01")
        for field in ("start_date", "end_date"):
            for value in invalid:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValidationError) as error:
                        self.request(**{field: value})
                    self.assertEqual(error.exception.errors()[0]["loc"], (field,))

    def test_existing_travel_day_limits_are_preserved(self):
        for value in (0, 31):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.request(travel_days=value)


if __name__ == "__main__":
    unittest.main()
