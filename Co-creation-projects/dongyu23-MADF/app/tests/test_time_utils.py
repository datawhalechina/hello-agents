import unittest
from app.core.time_utils import get_beijing_time
from datetime import datetime, timezone, timedelta

class TestTimeUtils(unittest.TestCase):
    def test_get_beijing_time(self):
        bj_time = get_beijing_time()
        # Verify timezone offset is +8
        self.assertEqual(bj_time.tzinfo, timezone(timedelta(hours=8)))
        
        # Verify it's close to current UTC time + 8 hours
        utc_now = datetime.now(timezone.utc)
        expected_bj = utc_now.astimezone(timezone(timedelta(hours=8)))
        
        # Allow small delta for execution time
        diff = abs((bj_time - expected_bj).total_seconds())
        self.assertLess(diff, 1.0)

if __name__ == '__main__':
    unittest.main()
