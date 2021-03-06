import json

from django.contrib.staticfiles.templatetags.staticfiles import static
from django.template.loader import render_to_string
from django.utils.six import python_2_unicode_compatible

from .widget import Widget


@python_2_unicode_compatible
class Map(Widget):
    """Leaflet map visualizing dataset.

    Can be used in pair with FilterForm.

    Values are taken from model latitude and longitude fields.
    If other fields define longitude and latitude,
    override description and coordinates methods.
    """

    name = None
    model = None
    filterform = None
    template_name = "django_data_explorer/map_widget.html"

    @staticmethod
    def description(model):
        """Return string description for given point."""
        return "{}, {}".format(model.latitude, model.longitude)

    @staticmethod
    def coordinates(model):
        """Return dictionary with keys latitude and longitude."""
        return {'latitude': model.latitude, 'longitude': model.longitude}

    def filter_data(self, data=None, queryset=None):
        data = data or {}
        if self.filterform is not None:
            return self.filterform.filter_queryset_query_string(
                data, queryset)
        return queryset

    def get_queryset(self, params):  # pylint: disable=unused-argument
        """Dummy queryset method returning all objects."""
        return self.model.objects.all()

    def get_data(self, client_params):
        queryset = self.get_queryset(self.params)
        map_data = self.filter_data(data=client_params, queryset=queryset)
        return self.parse_data(map_data)

    def parse_data(self, data):
        parsed_data = []
        for obj in data:
            dict_obj = {
                'description': self.description(obj)
            }
            dict_obj.update(self.coordinates(obj))
            parsed_data.append(dict_obj)
        return parsed_data

    def __str__(self):
        map_data = {
            'name': self.name,
            'endpoint': self.endpoint.get_url(),
            'params': json.dumps(self.params),
            'filter': self.filterform.filter_name if self.filterform is not None else "",
            'imageUrl': static("django_data_explorer/dist/images")
        }
        text = render_to_string(
            self.template_name, {'map_data': json.dumps(map_data),
                                 'name': self.name})
        return text

    def is_accessible(self, request):
        return True
