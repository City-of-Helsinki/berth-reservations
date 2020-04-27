import os
import shutil

from django.conf import settings
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from resources.models import (
    get_harbor_media_folder,
    get_winter_area_media_folder,
    Harbor,
    HarborMap,
    WinterStorageArea,
    WinterStorageAreaMap,
)
from utils.files import remove_file


@receiver(post_delete, sender=HarborMap)
@receiver(post_delete, sender=WinterStorageAreaMap)
def delete_map_file_handler(sender, instance, **kwargs):
    remove_file(instance, "map_file")


@receiver(pre_save, sender=WinterStorageArea)
@receiver(pre_save, sender=Harbor)
def delete_image_file_handler(sender, instance, **kwargs):
    previous_instance = sender.objects.filter(pk=instance.id).first()

    # The previous file should only be deleted if it's different from the new one
    # or if the new one removes the image (by setting it to None)
    if (
        previous_instance
        and previous_instance.image_file != instance.image_file
        or instance.image_file is None
    ):
        remove_file(previous_instance, "image_file")


@receiver(post_delete, sender=Harbor, dispatch_uid="post_delete_harbor")
def delete_harbor_media_directory_handler(sender, instance, **kwargs):
    path = os.path.join(settings.MEDIA_ROOT, get_harbor_media_folder(instance, ""))
    if os.path.exists(path):
        shutil.rmtree(path)


@receiver(post_delete, sender=WinterStorageArea, dispatch_uid="post_delete_wsa")
def delete_winter_area_media_directory_handler(sender, instance, **kwargs):
    path = os.path.join(settings.MEDIA_ROOT, get_winter_area_media_folder(instance, ""))
    if os.path.exists(path):
        shutil.rmtree(path)
