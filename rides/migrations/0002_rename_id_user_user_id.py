# Generated by Django 5.1.3 on 2024-11-28 09:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rides', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='id_user',
            new_name='id',
        ),
    ]