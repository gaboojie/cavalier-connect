# Generated by Django 4.2.15 on 2024-10-02 02:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myaccount", "0003_user_email_alter_user_username"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
    ]