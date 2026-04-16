from decimal import Decimal
from itertools import islice, product

from django.core.management.base import BaseCommand

from blog.models import Utilisateur


class Command(BaseCommand):
    help = "Create 100 fictitious utilisateurs."

    def handle(self, *args, **options):
        first_names = [
            "Antoine",
            "Enric",
            "Claire",
            "Julien",
            "Sophie",
            "Marc",
            "Lucie",
            "Nicolas",
            "Camille",
            "Thomas",
        ]
        last_names = [
            "Boullanger",
            "Lopez",
            "Martin",
            "Bernard",
            "Petit",
            "Moreau",
            "Fournier",
            "Girard",
            "Roux",
            "Lefevre",
        ]
        services = [
            "RH",
            "Direction",
            "IT",
            "Production",
        ]
        payes = [
            Decimal("2100.00"),
            Decimal("2300.00"),
            Decimal("2500.00"),
            Decimal("2700.00"),
            Decimal("2900.00"),
            Decimal("3100.00"),
            Decimal("3300.00"),
            Decimal("3500.00"),
        ]

        pairs = list(islice(product(first_names, last_names), 100))
        utilisateurs = []
        existing_emails = set(Utilisateur.objects.values_list("mail", flat=True))

        for idx, (first, last) in enumerate(pairs):
            nomprenom = f"{first} {last}"
            if idx == 0:
                mail = "antoinejeuxc@gmail.com"
            else:
                slug = f"{first}.{last}.{idx}".lower().replace(" ", "").replace("-", "")
                mail = f"{slug}@example.com"

            if mail in existing_emails:
                continue

            utilisateurs.append(
                Utilisateur(
                    nomprenom=nomprenom,
                    service=services[idx % len(services)],
                    mail=mail,
                    paye=payes[idx % len(payes)],
                )
            )
            existing_emails.add(mail)

        Utilisateur.objects.bulk_create(utilisateurs)
        self.stdout.write(
            self.style.SUCCESS(f"Utilisateurs created: {len(utilisateurs)}")
        )
