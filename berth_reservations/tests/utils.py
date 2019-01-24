def get(api_client, url, status_code=200):
    return _execute_request(api_client, 'get', url, status_code)


def post(api_client, url, data=None, status_code=201):
    return _execute_request(api_client, 'post', url, status_code, data)


def put(api_client, url, data=None, status_code=200):
    return _execute_request(api_client, 'put', url, status_code, data)


def patch(api_client, url, data=None, status_code=200):
    return _execute_request(api_client, 'patch', url, status_code, data)


def delete(api_client, url, status_code=204):
    return _execute_request(api_client, 'delete', url, status_code)


def _execute_request(api_client, method, url, status_code, data=None):
    response = getattr(api_client, method)(url, data=data)
    assert response.status_code == status_code, 'Expected status code {} but got {} with data {}'.format(
        status_code, response.status_code, response.data)
    return response.data


def check_disallowed_methods(api_client, urls, methods, status_code=405):
    if isinstance(urls, str):
        urls = (urls,)
    if isinstance(methods, str):
        methods = (methods,)

    for url in urls:
        for method in methods:
            response = getattr(api_client, method)(url)
            assert response.status_code == status_code, (
                '%s %s expected %s, but got %s %s'
                % (method, url, status_code, response.status_code, response.data)
            )
