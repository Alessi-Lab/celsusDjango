# Generated by Django 4.1.5 on 2023-02-17 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('celsus', '0053_alter_collaborator_project_alter_curtain_project_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataFilterList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
                ('data', models.TextField()),
            ],
        ),
    ]
