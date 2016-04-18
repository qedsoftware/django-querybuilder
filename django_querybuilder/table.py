import operator
import functools

from django.utils.encoding import smart_text
from django.utils.six import python_2_unicode_compatible

from datatableview.datatables import LegacyDatatable


class QuerysetDatatable(LegacyDatatable):
    def __init__(self, object_list=(), url='', *args, **kwargs):
        super(QuerysetDatatable, self).__init__(
            object_list, url, *args, **kwargs)
        self.allowed_options = [
            'search', 'start_offset', 'page_length', 'ordering', 'filters']

    def normalize_config(self, config, query_config):
        if config['hidden_columns'] is None:
            config['hidden_columns'] = []
        if config['search_fields'] is None:
            config['search_fields'] = []
        if config['unsortable_columns'] is None:
            config['unsortable_columns'] = []

        for option in self.allowed_options:
            normalizer_f = getattr(self, 'normalize_config_{}'.format(option))
            config[option] = normalizer_f(config, query_config)
        return config

    @staticmethod
    def normalize_config_filters(dummy, query_config):
        filters = []
        filters_input = query_config.get('filters', None)
        if filters_input:
            for filter_params in filters_input.split(','):
                column_name, lookup, term = filter_params.split(';')
                filters.append((column_name, lookup, term))
        return filters

    def search_column(self, column, terms, lookup_types):
        return column.search(self.model, terms, lookup_types)

    def search(self, queryset):
        table_queries = []

        for column_name, lookup, term in self.config['filters']:
            column = self.columns[column_name]
            search_f = getattr(
                self, 'search_%s' % (column_name), self.search_column)
            query = search_f(column, term, [lookup])
            if query is not None:
                table_queries.append(query)

        if table_queries:
            query = functools.reduce(operator.and_, table_queries)
            queryset = queryset.filter(query)

        return queryset

    def get_records_list(self):
        return self._records


def parse_data(records):
    data = []
    for record in records:
        for attr in ['pk', '_extra_data']:
            record.pop(attr)
        data.append(dict(record))
    return data


@python_2_unicode_compatible
class Table(object):
    def __init__(self, name, model, columns=None):
        """
        :param columns: columns to display, (column header, model field) list
                        all model fields by default
                        supports related field
        """
        self.name = name
        self.model = model
        self.columns = columns

    def get_datatable(self, query_config):
        class ModelQuerysetDatatable(QuerysetDatatable):
            class Meta(object):
                model = self.model
                columns = self.columns
        datatable = ModelQuerysetDatatable(self.model.objects.all(),
                                           self.get_endpoint_url(),
                                           query_config=query_config)
        return datatable

    def filter_queryset(self, query_config):
        datatable = self.get_datatable(query_config)
        datatable.populate_records()
        return list(datatable.get_records_list())

    def get_data(self, query_config):
        datatable = self.get_datatable(query_config)
        datatable.populate_records()
        return parse_data(datatable.get_records())

    def get_endpoint_url(self):
        return "/querybuilder/querybuilder-endpoint-%s" % (self.name)

    def __str__(self):
        return smart_text(self.get_datatable({}))
