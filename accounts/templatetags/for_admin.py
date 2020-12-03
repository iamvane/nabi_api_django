from django.template import Library
from django.contrib.admin.views.main import SEARCH_VAR
from django.contrib.admin.templatetags.base import InclusionAdminNode
# from django.contrib.admin.templatetags.admin_list import search_form

register = Library()


def search_form(location, places, cl):
    """
    Display a search form for searching the list.
    """
    return {
        'cl': cl,
        'show_result_count': cl.result_count != cl.full_result_count,
        'search_var': SEARCH_VAR,
        'location_values': location,
        'places_values': places
    }


@register.tag(name='search_form')
def search_form_tag(parser, token):
    return InclusionAdminNode(parser, token, func=search_form, template_name='search_form.html', takes_context=False)
