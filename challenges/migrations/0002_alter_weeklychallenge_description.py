# Generated manually: migrate description field from django-ckeditor to django-ckeditor-5

import django_ckeditor_5.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("challenges", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="weeklychallenge",
            name="description",
            field=django_ckeditor_5.fields.CKEditor5Field(
                config_name="default", verbose_name="Description"
            ),
        ),
    ]
