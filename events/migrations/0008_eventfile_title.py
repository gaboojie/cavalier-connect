# Generated by Django 4.2.16 on 2024-11-02 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0007_remove_eventfile_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventfile',
            name='title',
            field=models.CharField(default='Untitled', max_length=100),
        ),
    ]
