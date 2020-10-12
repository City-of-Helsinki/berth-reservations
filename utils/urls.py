from django.conf import settings


def get_image_file_url(image_file) -> str:
    return settings.VENE_UI_URL + image_file
