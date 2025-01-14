# Generated by Django 4.1.4 on 2024-10-01 02:49

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=250)),
                ('last_name', models.CharField(max_length=250)),
                ('username', models.CharField(max_length=250)),
                ('password', models.CharField(max_length=128)),
                ('student_id', models.CharField(max_length=20, unique=True)),
                ('role', models.IntegerField(choices=[(0, 'Anonymous'), (1, 'Common User'), (2, 'PMA Administrator'), (3, 'Django Administrator')], default=0)),
                ('date_of_birth', models.DateField()),
                ('created_timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('authenticated_with_google', models.BooleanField(default=False)),
            ],
        ),
    ]