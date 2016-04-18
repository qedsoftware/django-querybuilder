import datetime
import json

import mock
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.encoding import smart_text

import django_querybuilder
from django_querybuilder import FilterForm

from .models import Author, Book, City
from .querybuilder import BasicBookTable, BookFilter, CityMap
from .views import BookEndpoint


class TableFiltersTestCase(TestCase):
    def setUp(self):
        self.fakeauthor = Author.objects.create(name="FakeAuthor")
        self.fakeauthor2 = Author.objects.create(name="FakeAuthor2")
        self.testbook1 = Book.objects.create(
            title="TestBook1", pages=20, author=self.fakeauthor)
        self.testbook2 = Book.objects.create(
            title="TestBook2", author=self.fakeauthor, pages=10)
        self.nontestbook = Book.objects.create(
            title="nonTestBook", author=self.fakeauthor2)
        self.objects_list = [self.testbook1, self.testbook2, self.nontestbook]

    def test_no_filters(self):
        self._assert_filtered_book_table({}, self.objects_list)

    def test_single_text_filter(self):
        self._assert_filtered_book_table(
            {'filters': 'title;exact;TestBook1'},
            [self.testbook1]
        )
        self._assert_filtered_book_table(
            {'filters': 'title;startswith;TestBook'},
            [self.testbook1, self.testbook2]
        )
        self._assert_filtered_book_table(
            {'filters': 'title;contains;TestBook'},
            self.objects_list
        )

    def test_multiple_filters(self):
        self._assert_filtered_book_table(
            {'filters': 'title;exact;TestBook1,pages;exact;20'},
            [self.testbook1]
        )

    def _assert_filtered_book_table(self, query_config, expected):
        table = BasicBookTable
        records = table.filter_queryset(query_config)
        self.assertEqual(records, expected)


class TableEndpointView(TestCase):
    def setUp(self):
        self.fakeauthor = Author.objects.create(name="FakeAuthor")
        self.testbook1 = Book.objects.create(
            title="TestBook1", pages=20, author=self.fakeauthor)
        self.testbook2 = Book.objects.create(
            title="TestBook2", pages=200, author=self.fakeauthor)
        self.view = BookEndpoint
        self.url = reverse('book-endpoint')

    def test_basic_view(self):
        data = self.get_data_from_response({})
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['1'], "TestBook1")
        self.assertEqual(data[1]['1'], "TestBook2")

    def test_filtered_view(self):
        data = self.get_data_from_response(
            {'filters': 'title;exact;TestBook1'}
        )
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['1'], "TestBook1")

    def test_filtered_view_no_results(self):
        data = self.get_data_from_response(
            {'filters': 'title;exact;TestBook1,title;exact;fakefake'}
        )
        self.assertEqual(len(data), 0)

    def get_data_from_response(self, params):
        response = self.client.get(
            self.url, params, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        content = json.loads(response.content.decode())
        return content["data"]


class TableStrRepresentation(TestCase):
    def test_str(self):
        text = smart_text(BasicBookTable)
        self.assertIn("Title", text)


class FilterFormTestCase(TestCase):
    def setUp(self):
        self.author1 = Author.objects.create(name="Author_1")
        self.author2 = Author.objects.create(name="Author_2")
        self.testbook1 = Book.objects.create(
            title="Book_1", pages=20, author=self.author1)
        self.testbook2 = Book.objects.create(
            title="Book_2", author=self.author2, pages=10)
        self.testbook3 = Book.objects.create(
            title="Book_3", author=self.author2,
            publication_date=datetime.date(2008, 6, 24))

    def test_filter_lt_condition(self):
        filterform = BookFilter()
        filter_data = {'pages__lt': '15'}
        filtered = filterform.filter_queryset(filter_data, Book.objects.all())
        self.assertQuerysetEqual(
            filtered, ['Book_2'], lambda b: b.title, False)

    def test_filter_no_results(self):
        filterform = BookFilter()
        filter_data = {'pages__gt': '25'}
        filtered = filterform.filter_queryset(filter_data, Book.objects.all())
        self.assertQuerysetEqual(filtered, [], lambda b: b.title, False)

    def test_empty_filter(self):
        filterform = BookFilter()
        filter_data = {}
        filtered = filterform.filter_queryset(filter_data, Book.objects.all())
        self.assertQuerysetEqual(
            filtered, ['Book_1', 'Book_2', 'Book_3'], lambda b: b.title, False)

    def test_excluding_filter(self):
        filterform = BookFilter()
        filter_data = {
            'pages__gt': 15,
            'pages__lt': 14,
        }
        filtered = filterform.filter_queryset(filter_data, Book.objects.all())
        self.assertQuerysetEqual(filtered, [], lambda b: b.title, False)

    def test_filter_exact(self):
        filterform = BookFilter()
        filter_data = {
            'publication_date': '2008-06-24',
            'publication_date__year': 2008,
        }
        filtered = filterform.filter_queryset(filter_data, Book.objects.all())
        self.assertQuerysetEqual(
            filtered, ['Book_3'], lambda b: b.title, False)

    @mock.patch("django_querybuilder.FilterForm.filter_queryset")
    def test_filter_queryset_query_string(self, filter_queryset_mock):
        filterform = BookFilter()
        filterform.filter_queryset_query_string("a=b&c=d", "queryset here")
        parsed = filter_queryset_mock.call_args[0][0]
        self.assertEqual(parsed, {"a": ["b"], "c": ["d"]})

    def test_parse_form(self):
        class SimpleFilter(FilterForm):
            class Meta(object):
                model = Book
                fields = {
                    'pages': ['exact', 'gt'],
                }
        filterform = SimpleFilter()
        parsed = '<filter-form id="filter_ff">\n\n    <form id="filter">\n        ' \
             '<div class="ff-group"><p><label for="id_pages">Pages:</label> ' \
             '<input id="id_pages" name="pages" step="any" type="number" /></p></div>\n' \
             '<div class="ff-group"><p><label for="id_pages__gt">Pages:</label> ' \
             '<input id="id_pages__gt" name="pages__gt" step="any" type="number" /></p></div>\n' \
             '        <input type="submit" />\n    ' \
             '</form>\n\n</filter-form>'
        self.assertEqual(str(filterform), parsed)


class MapGetDataTestCase(TestCase):
    def setUp(self):
        self.city1 = City.objects.create(name="City_1", citizens_number=3,
                                         latitude=30.0, longitude=20.0)
        self.city2 = City.objects.create(name="City_2", citizens_number=33,
                                         latitude=33.0, longitude=21.0)
        self.city3 = City.objects.create(name="City_3", citizens_number=333,
                                         latitude=35.0, longitude=22.0)

    def test_get_all_data(self):
        city_map = CityMap
        query_config = {}
        data = city_map.get_data(query_config)
        self.assertEqual(data, [
            {'description': "City City_1 with latitude 30 " +
                            "and longitude 20",
             'latitude': 30.0, 'longitude': 20.0},
            {'description': "City City_2 with latitude 33 " +
                            "and longitude 21",
             'latitude': 33.0, 'longitude': 21.0},
            {'description': "City City_3 with latitude 35 " +
                            "and longitude 22",
             'latitude': 35.0, 'longitude': 22.0}])

    def test_get_some_data(self):
        city_map = CityMap
        query_config = 'citizens_number__gt=30&latitude__lt=34.0'
        data = city_map.get_data(query_config)
        self.assertEqual(data[0]['latitude'], 33.0)

    def test_get_no_data(self):
        city_map = CityMap
        query_config = 'citizens_number__gt=30&latitude__lt=20.0'
        data = city_map.get_data(query_config)
        self.assertEqual(data, [])

    @staticmethod
    def test_map_no_descr():
        """Make sure that the constructor works for maps without descriptions.
        """
        django_querybuilder.Map("nonexistent", City)
