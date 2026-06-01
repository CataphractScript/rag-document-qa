from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(help_text="Human-readable title for the document.", max_length=255)),
                ("content", models.TextField(help_text="Full extracted text content of the document.")),
                ("file", models.FileField(blank=True, help_text="Original .docx file (optional).", null=True, upload_to="documents/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Document",
                "verbose_name_plural": "Documents",
                "ordering": ["-created_at"],
            },
        ),
    ]
