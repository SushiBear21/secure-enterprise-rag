import unittest

from app.authorization import AccessDenied, allowed_audiences


class AuthorizationTests(unittest.TestCase):
    def test_employee_gets_only_general_documents(self):
        self.assertEqual(
            allowed_audiences(["employees"]),
            ["all_employees"],
        )

    def test_soc_gets_general_and_soc_documents(self):
        self.assertEqual(
            allowed_audiences(["soc_analysts"]),
            ["all_employees", "soc_analysts"],
        )

    def test_multiple_groups_combine_permissions(self):
        self.assertEqual(
            allowed_audiences(["soc_analysts", "acquisition_team"]),
            ["acquisition_team", "all_employees", "soc_analysts"],
        )

    def test_missing_unknown_or_malformed_groups_are_denied(self):
        for groups in [
            [],
            ["administrators"],
            ["soc_analysts_fake"],
            "soc_analysts",
            None,
            [123],
        ]:
            with self.subTest(groups=groups):
                with self.assertRaises(AccessDenied):
                    allowed_audiences(groups)


if __name__ == "__main__":
    unittest.main()