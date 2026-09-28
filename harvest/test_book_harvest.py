from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from harvest.harvesters.book import iter_changes
from harvest.tasks import harvest_single_book_in_couchdb


class BookHarvestTests(SimpleTestCase):
    @patch("harvest.harvesters.book.fetch_changes_page")
    @patch("harvest.harvesters.book._base_url", return_value="https://books.example")
    def test_changes_continue_from_last_item_seq(self, _base_url, fetch_page):
        fetch_page.side_effect = [
            {"results": [{"id": "book-1", "seq": 1}], "last_seq": 99},
            {"results": [{"id": "book-2", "seq": 2}], "last_seq": 99},
            {"results": []},
        ]

        changes = list(iter_changes(since=0, limit=1))

        self.assertEqual([change["id"] for change in changes], ["book-1", "book-2"])
        self.assertEqual(
            [entry.kwargs["since"] for entry in fetch_page.call_args_list],
            [0, 1, 2],
        )

    @patch("harvest.tasks.transform_indexed_page")
    @patch("harvest.tasks.harvest_single_book")
    @patch("harvest.tasks.User.objects.get")
    def test_single_book_task_transforms_after_raw_indexing(
        self, _get_user, harvest_book, transform_page
    ):
        book = MagicMock(identifier="book-1")
        book.is_indexed.return_value = True
        harvest_book.return_value = book

        harvest_single_book_in_couchdb(username="collector", payload={"id": "book-1"})

        transform_page.assert_called_once_with("HarvestedBook", ["book-1"])
