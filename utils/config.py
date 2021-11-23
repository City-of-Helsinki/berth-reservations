import environ
from django.conf import settings


def get_config_from_env(template: dict) -> dict:
    env = environ.Env(**template)

    config = {}
    for key in template.keys():
        if hasattr(settings, key):
            config[key] = getattr(settings, key)
        else:
            config[key] = env(key)

    return config
