"""
Management command: index_documents

Rebuilds the entire FAISS vector store from all documents in the database.
Useful after:
  - importing documents directly into the DB
  - upgrading the embedding model
  - recovering from a corrupted index

Usage:
  docker-compose exec web python manage.py index_documents
"""

import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rebuild the FAISS vector index from all documents in the database."

    def handle(self, *args, **options):
        self.stdout.write("Starting document indexing...")
        try:
            from documents.services import reindex_all_documents
            reindex_all_documents()
            self.stdout.write(self.style.SUCCESS("Indexing complete."))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Indexing failed: {exc}"))
            raise
