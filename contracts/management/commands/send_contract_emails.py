from django.core.management import BaseCommand
from django_ilmoitin.utils import send_mail

from contracts.enums import ContractStatus
from leases.enums import LeaseStatus
from leases.models import BerthLease


class Command(BaseCommand):
    help = "Sends missing contract signature emails"

    def handle(self, *args, **options):
        paid_renewed_leases = BerthLease.objects.filter(
            status=LeaseStatus.PAID, start_date__year=2021, contract__isnull=False
        )

        count = 0

        for paid_renewed_lease in paid_renewed_leases:

            if paid_renewed_lease.contract.status != ContractStatus.SIGNED:
                email_address = paid_renewed_lease.order.customer_email
                order_number = paid_renewed_lease.order.order_number
                email_content = (
                    "FI\n\n"
                    "Hei.\n\n"
                    "Olet maksanut venepaikkalaskun. Pahoittelemme virhettämme jonka johdosta "
                    "allekirjoitus jäi tekemättä."
                    "Käythän vielä allekirjoittamassa uuden sopimuksen liittyen venepaikkaasi. "
                    "Allekirjoittaminen on pakollista ja vuokrasopimus on voimassa vasta allekirjoituksen jälkeen.\n\n"
                    f"Siirry allekirjoitukseen: https://venepaikat.hel.fi/fi/payment?order_number={order_number}\n\n"
                    "EN\n\n"
                    "Hi.\n\n"
                    "You have paid the boat berth invoice. Apologies but the contract is not yet signed because of our "
                    "mistake. Please sign the corresponding contract for the berth. Signature is obligatory and "
                    "contract is valid only after signing it.\n\n"
                    f"Continue to the signature: https://venepaikat.hel.fi/en/payment?order_number={order_number}\n\n"
                    "SV\n\n"
                    "Hej.\n\n"
                    "Du har betalat båtplatsens faktura. Ber om ursäkt men kontraktet är ännu inte undertecknat på "
                    "grund av vårt misstag. Vänligen underteckna motsvarande kontrakt för båtplatsen. Underskrift är "
                    "obligatoriskt och kontraktet är giltigt först efter undertecknandet.\n\n"
                    f"Fortsätt till signaturen: https://venepaikat.hel.fi/sv/payment?order_number={order_number}\n\n"
                )
                email_subject = (
                    "Venepaikan vuokrasopimusehdot / Berth lease terms / "
                    "Avtalsvillkor för uthyrning av båtplats"
                )

                try:
                    send_mail(email_subject, email_content, email_address)
                    count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Failed to send email to address {email_address}: {str(e)}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS(f"{count} contract emails sent"))
