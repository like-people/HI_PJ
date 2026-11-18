"""기능 2: 분류 규칙(features/categorize.py) 테스트.

지출은 자료에 직접 넣어서(기능 1 없이도) 확인한다.
실행: python -m unittest discover -s tests -v
"""

import unittest

from helpers import NAMES, StoreCase

from moim.features import categorize

KIM = NAMES[0]
LEE = NAMES[1]


class CategorizeCase(StoreCase):
    def put(self, eid, amount=9000, memo="", payer=KIM, category=None, fixed=None, deleted=None):
        e = {"id": eid, "date": "2026-11-10", "payer": payer, "amount": amount,
             "members": list(NAMES), "category": category, "memo": memo}
        if fixed is not None:
            e["category_fixed"] = fixed
        if deleted is not None:
            e["deleted"] = deleted
        self.store.data["expenses"].append(e)
        return e


class Rules(CategorizeCase):
    def test_add_and_remove(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        categorize.add_rule(rules, "교통", ["택시"])
        categorize.remove_rule(rules, 0)
        self.assertEqual([r["category"] for r in rules], ["교통"])

    def test_save_and_load(self):
        rules = []
        categorize.add_rule(rules, "교통", ["택시"], priority=2, payer=KIM, min_amount=1000)
        categorize.save_rules(self.cfg["rules"], rules)
        self.assertEqual(categorize.load_rules(self.cfg["rules"]), rules)

    def test_load_missing_file_is_empty(self):
        self.assertEqual(categorize.load_rules(self.path("none.json")), [])


class Classify(CategorizeCase):
    def test_keyword_any(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁", "점심"])
        self.assertEqual(categorize.classify(self.put(1, memo="팀 점심"), rules), "식비")

    def test_no_match_is_none(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        self.assertIsNone(categorize.classify(self.put(1, memo="현수막"), rules))

    def test_higher_priority_wins(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"], priority=0)
        categorize.add_rule(rules, "회식", ["저녁"], priority=1)
        self.assertEqual(categorize.classify(self.put(1, memo="저녁"), rules), "회식")

    def test_same_priority_first_registered_wins(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        categorize.add_rule(rules, "회식", ["저녁"])
        self.assertEqual(categorize.classify(self.put(1, memo="저녁"), rules), "식비")

    def test_payer_and_amount_conditions(self):
        rules = []
        categorize.add_rule(rules, "큰지출", payer=KIM, min_amount=10000, max_amount=20000)
        self.assertEqual(categorize.classify(self.put(1, amount=10000), rules), "큰지출")
        self.assertEqual(categorize.classify(self.put(2, amount=20000), rules), "큰지출")
        self.assertIsNone(categorize.classify(self.put(3, amount=9999), rules))
        self.assertIsNone(categorize.classify(self.put(4, amount=20001), rules))
        self.assertIsNone(categorize.classify(self.put(5, amount=15000, payer=LEE), rules))


class ApplyRules(CategorizeCase):
    def setUp(self):
        super().setUp()
        self.rules = []
        categorize.add_rule(self.rules, "식비", ["저녁"])

    def test_apply_changes_and_returns_list(self):
        self.put(1, memo="저녁")
        self.assertEqual(categorize.apply_rules(self.store, self.rules), [(1, "미분류", "식비")])
        self.assertEqual(self.store.data["expenses"][0]["category"], "식비")

    def test_preview_does_not_change(self):
        self.put(1, memo="저녁")
        self.assertEqual(categorize.apply_rules(self.store, self.rules, preview=True), [(1, "미분류", "식비")])
        self.assertIsNone(self.store.data["expenses"][0]["category"])

    def test_fixed_is_skipped(self):
        self.put(1, memo="저녁", category="기타", fixed=True)
        self.assertEqual(categorize.apply_rules(self.store, self.rules), [])
        self.assertEqual(self.store.data["expenses"][0]["category"], "기타")

    def test_deleted_is_skipped(self):
        self.put(1, memo="저녁", deleted=True)
        self.assertEqual(categorize.apply_rules(self.store, self.rules), [])

    def test_no_match_keeps_existing_category(self):
        self.put(1, memo="현수막", category="기타")
        self.assertEqual(categorize.apply_rules(self.store, self.rules), [])
        self.assertEqual(self.store.data["expenses"][0]["category"], "기타")


class SetCategory(CategorizeCase):
    def test_set_fixes_category(self):
        self.put(1, memo="저녁")
        categorize.set_category(self.store, 1, "기타")
        e = self.store.data["expenses"][0]
        self.assertEqual((e["category"], e["category_fixed"]), ("기타", True))

    def test_unfix(self):
        self.put(1)
        categorize.set_category(self.store, 1, "기타")
        categorize.unfix_category(self.store, 1)
        self.assertFalse(self.store.data["expenses"][0]["category_fixed"])

    def test_direct_uncategorized_is_allowed_as_none(self):
        self.put(1, category="식비")
        categorize.set_category(self.store, 1, "미분류")
        self.assertIsNone(self.store.data["expenses"][0]["category"])

    def test_empty_name_rejected(self):
        self.put(1)
        with self.assertRaises(ValueError):
            categorize.set_category(self.store, 1, "  ")

    def test_unknown_id_rejected(self):
        with self.assertRaises(ValueError):
            categorize.set_category(self.store, 99, "식비")


class Lists(CategorizeCase):
    def test_uncategorized_list(self):
        self.put(1, category="식비")
        self.put(2)
        self.put(3, category="미분류")
        self.put(4, deleted=True)
        self.assertEqual([e["id"] for e in categorize.uncategorized(self.store)], [2, 3])

    def test_overlaps(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁", "점심"])
        categorize.add_rule(rules, "회식", ["저녁"])
        categorize.add_rule(rules, "식비", ["저녁"])
        self.assertEqual(categorize.overlaps(rules), [(0, 1, "저녁"), (1, 2, "저녁")])


class LockedPeriod(CategorizeCase):
    """정산이 확정된 기간의 지출은 분류를 바꿀 수 없다(규약 6절)."""

    def setUp(self):
        super().setUp()
        self.store.data["locks"] = [{"start": "2026-11-01", "end": "2026-11-30"}]

    def test_apply_rules_skips_locked(self):
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        self.put(1, memo="저녁")
        self.assertEqual(categorize.apply_rules(self.store, rules), [])
        self.assertIsNone(self.store.data["expenses"][0]["category"])

    def test_set_category_rejected_when_locked(self):
        self.put(1)
        with self.assertRaises(ValueError):
            categorize.set_category(self.store, 1, "식비")

    def test_unfix_category_rejected_when_locked(self):
        self.put(1, category="식비", fixed=True)
        with self.assertRaises(ValueError):
            categorize.unfix_category(self.store, 1)
        self.assertTrue(self.store.data["expenses"][0]["category_fixed"])

    def test_outside_locked_period_is_allowed(self):
        e = self.put(1, memo="저녁")
        e["date"] = "2026-12-01"
        rules = []
        categorize.add_rule(rules, "식비", ["저녁"])
        self.assertEqual(categorize.apply_rules(self.store, rules), [(1, "미분류", "식비")])
        categorize.set_category(self.store, 1, "기타")
        self.assertEqual(self.store.data["expenses"][0]["category"], "기타")


if __name__ == "__main__":
    unittest.main()