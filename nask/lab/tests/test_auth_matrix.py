import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auth_matrix import classify

class Tests(unittest.TestCase):
    def test_private_access_is_only_a_hypothesis(self):
        self.assertEqual(classify(200, 200, 'private'), 'review_required_not_a_finding')
    def test_private_denial_and_hidden(self):
        for code in (401, 403, 404):
            self.assertEqual(classify(200, code, 'private'), 'access_denied_or_hidden')
    def test_shared_access_is_not_idor(self):
        self.assertEqual(classify(200, 200, 'shared'), 'consistent_with_shared_access')
        self.assertEqual(classify(200, 403, 'shared'), 'unexpected_denial_check_setup')
    def test_failed_owner_or_error_inconclusive(self):
        self.assertEqual(classify(403, 200, 'private'), 'inconclusive')
        self.assertEqual(classify(200, 500, 'private'), 'inconclusive')
        self.assertEqual(classify(200, 200, 'unknown'), 'inconclusive')
    def test_reject_bad_input(self):
        for values in [(True, 200, 'private'), (99, 200, 'private'), (200, 600, 'private'), (200, 200, 'other')]:
            with self.subTest(values=values), self.assertRaises(ValueError): classify(*values)

if __name__ == '__main__': unittest.main()
