"""지출 하위 명령을 통합 실행 흐름으로 검증한다."""

from unittest.mock import patch

from helpers import NAMES, StoreCase
from moim.cli import main
from moim.common.store import Store


class ExpenseCommandTests(StoreCase):
    def setUp(self):
        super().setUp()
        self.store.save()
        self.output = []

    def run_exp(self, *args):
        self.output.clear()
        return main(["--config", self.path("config.json"), "exp", *args], self.output.append)

    def add_expense(self, day="2026-11-12"):
        return self.run_exp(
            "add", "--date", day, "--payer", NAMES[0],
            "--amount", "3,000", "--members", ";".join(NAMES[:2]),
            "--weights", f"{NAMES[0]}=2;{NAMES[1]}=1", "--memo", "회식",
        )

    def test_add_parses_and_saves_expense(self):
        self.assertEqual(self.add_expense(), 0)
        expense = Store(self.store.path).load().get_expense(1)
        self.assertEqual(expense["amount"], 3000)
        self.assertEqual(expense["members"], NAMES[:2])
        self.assertEqual(expense["weights"], {NAMES[0]: 2, NAMES[1]: 1})
        self.assertEqual(expense["memo"], "회식")

    def test_list_sorts_and_does_not_save(self):
        self.assertEqual(self.add_expense("2026-11-20"), 0)
        self.assertEqual(self.add_expense("2026-11-05"), 0)
        with patch.object(Store, "save", side_effect=AssertionError("조회 중 저장")):
            self.assertEqual(self.run_exp("list", "--order", "date"), 0)
        listing = self.output[0]
        self.assertLess(listing.index("2026-11-05"), listing.index("2026-11-20"))
        self.assertIn("3,000", listing)

    def test_edit_preserves_omitted_weights_and_can_clear_them(self):
        self.assertEqual(self.add_expense(), 0)
        self.assertEqual(self.run_exp("edit", "1", "--amount", "4500"), 0)
        expense = Store(self.store.path).load().get_expense(1)
        self.assertEqual(expense["amount"], 4500)
        self.assertEqual(expense["weights"], {NAMES[0]: 2, NAMES[1]: 1})

        self.assertEqual(self.run_exp("edit", "1", "--members", NAMES[0], "--equal"), 0)
        expense = Store(self.store.path).load().get_expense(1)
        self.assertEqual(expense["members"], [NAMES[0]])
        self.assertIsNone(expense["weights"])

    def test_delete_is_saved_and_hidden_from_list(self):
        self.assertEqual(self.add_expense(), 0)
        self.assertEqual(self.run_exp("delete", "1"), 0)
        self.assertTrue(Store(self.store.path).load().get_expense(1)["deleted"])
        self.assertEqual(self.run_exp("list"), 0)
        self.assertEqual(self.output, ["등록된 지출이 없습니다."])
        with patch.object(Store, "save", side_effect=AssertionError("이미 삭제한 지출을 다시 저장")):
            self.assertEqual(self.run_exp("delete", "1"), 0)

    def test_invalid_amount_is_reported_without_saving(self):
        with patch.object(Store, "save", side_effect=AssertionError("검증 실패 후 저장")):
            status = self.run_exp(
                "add", "--date", "2026-11-12", "--payer", NAMES[0],
                "--amount", "0", "--members", NAMES[0],
            )
        self.assertEqual(status, 1)
        self.assertTrue(self.output[0].startswith("오류: "))
        self.assertEqual(Store(self.store.path).load().data["expenses"], [])
