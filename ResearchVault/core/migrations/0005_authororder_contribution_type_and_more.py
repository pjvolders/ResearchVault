# Generated by Django 4.2.20 on 2025-03-12 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20250311_1942'),
    ]

    operations = [
        migrations.AddField(
            model_name='authororder',
            name='contribution_type',
            field=models.CharField(choices=[('normal', 'Normal'), ('first', 'First Author'), ('co-first', 'Co-First Author'), ('last', 'Last Author'), ('co-last', 'Co-Last Author'), ('corresponding', 'Corresponding Author')], default='normal', help_text='Type of author contribution', max_length=20),
        ),
    ]