# Generated by Django 4.2.15 on 2024-11-07 05:01

from django.db import migrations, models
import myaccount.models


class Migration(migrations.Migration):

    dependencies = [
        ("myaccount", "0012_profilepicture"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profilepicture",
            name="profile_picture",
            field=models.FileField(upload_to=myaccount.models.profile_picture_path),
        ),
    ]