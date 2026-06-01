"""
Management command: create_default_superuser

Creates a default admin superuser if none exists.
Credentials: admin / admin123 (change immediately in production!)

Usage: python manage.py create_default_superuser
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create a default superuser (admin/admin123) if no superuser exists."

    def handle(self, *args, **options):
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="admin123",
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Superuser created: username=admin, password=admin123\n"
                    "⚠️  Change this password immediately in production!"
                )
            )
        else:
            self.stdout.write("Superuser already exists; skipping.")
