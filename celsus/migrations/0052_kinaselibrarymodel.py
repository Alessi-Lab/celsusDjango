# Generated by Django 4.1.5 on 2023-01-14 13:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('celsus', '0051_alter_rawdata_value'),
    ]

    operations = [
        migrations.CreateModel(
            name='KinaseLibraryModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry', models.TextField()),
                ('position', models.IntegerField()),
                ('residue', models.CharField(max_length=1)),
                ('data', models.TextField()),
            ],
        ),
    ]
