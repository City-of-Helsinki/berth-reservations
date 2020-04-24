from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from customers.models import BoatCertificate
from utils.files import remove_file


@receiver(post_delete, sender=BoatCertificate)
def delete_boat_certificate_file_handler(sender, instance, **kwargs):
    remove_file(instance, "file")


@receiver(pre_save, sender=BoatCertificate)
def replace_boat_certificate_file_handler(sender, instance, **kwargs):
    previous_instance = sender.objects.filter(pk=instance.id).first()

    # The previous file should only be deleted if it's different from the new one
    # or if the new one removes the image (by setting it to None)
    if (
        previous_instance
        and previous_instance.file != instance.file
        or instance.file is None
    ):
        remove_file(previous_instance, "file")
