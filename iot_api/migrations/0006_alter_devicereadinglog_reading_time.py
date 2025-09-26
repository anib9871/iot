from django.db import migrations, models
import datetime

def convert_int_to_time(apps, schema_editor):
    DeviceReadingLog = apps.get_model('iot_api', 'DeviceReadingLog')
    for obj in DeviceReadingLog.objects.all():
        # Assuming integer stored as HHMM
        hh = obj.READING_TIME // 100
        mm = obj.READING_TIME % 100
        obj.READING_TIME = datetime.time(hour=hh, minute=mm)
        obj.save()

class Migration(migrations.Migration):

    dependencies = [
        ('iot_api', '0005_alter_devicereadinglog_reading_date_and_more'),
    ]

    operations = [
        migrations.RunPython(convert_int_to_time),
    ]
