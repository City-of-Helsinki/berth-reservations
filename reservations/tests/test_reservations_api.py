from rest_framework.reverse import reverse

from berth_reservations.tests.utils import check_disallowed_methods

RESERVATION_URL = reverse('reservation-list')


def test_concepts_of_interest_readonly(api_client):
    list_disallowed_methods = ('get', 'put', 'patch', 'delete')
    check_disallowed_methods(api_client, RESERVATION_URL, list_disallowed_methods)
