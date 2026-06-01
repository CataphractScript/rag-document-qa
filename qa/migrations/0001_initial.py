from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("documents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.TextField(help_text="The user's question.")),
                ("answer", models.TextField(help_text="The LLM-generated answer.")),
                ("source_documents", models.ManyToManyField(
                    blank=True,
                    help_text="Documents whose chunks were used as context.",
                    related_name="question_answers",
                    to="documents.document",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Q&A Record",
                "verbose_name_plural": "Q&A History",
                "ordering": ["-created_at"],
            },
        ),
    ]
