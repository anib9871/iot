# iot_api/models.py
from django.db import models

from django.utils import timezone
from datetime import datetime
import requests
from django.core.mail import send_mail

# ================== SMS Config ==================
SMS_API_URL = "http://www.universalsmsadvertising.com/universalsmsapi.php"
SMS_USER = "8960853914"
SMS_PASS = "8960853914"
SENDER_ID = "FRTLLP"

# ================== EMAIL CONFIG ==================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'testwebservice71@gmail.com'
EMAIL_HOST_PASSWORD = 'akuu vulg ejlg ysbt'  # Gmail app password

# ================== SMS Function ==================
def send_sms(phone, message):
    params = {
        "user_name": SMS_USER,
        "user_password": SMS_PASS,
        "mobile": phone,
        "sender_id": SENDER_ID,
        "type": "F",
        "text": message
    }
    try:
        resp = requests.get(SMS_API_URL, params=params, timeout=10)
        print("🔎 SMS API Response:", resp.text)
        if resp.status_code == 200 and ("success" in resp.text.lower() or "sent" in resp.text.lower()):
            print(f"✅ SMS sent to {phone}")
            return True
        else:
            print(f"❌ SMS failed for {phone}")
    except Exception as e:
        print("❌ SMS Error:", e)
    return False

# ================== Email Function ==================
def send_email_notification(subject, message, emails):
    try:
        send_mail(subject, message, "noreply@iot.com", emails)
        print(f"📧 Email sent to: {', '.join(emails)}")
        return True
    except Exception as e:
        print("❌ Email Error:", e)
        return False

# ================== Alarm Normalized Alert ==================
def send_normalized_alert(active_alarm):
    from .models import MasterDevice, UserOrganizationCentreLink, MasterUser  # Import here to avoid circular imports

    device = MasterDevice.objects.filter(DEVICE_ID=active_alarm.DEVICE_ID).first()
    if not device:
        print("❌ Device not found")
        return

    dev_name = device.DEVICE_NAME
    org_id = device.ORGANIZATION_ID
    centre_id = device.CENTRE_ID

    user_ids = list(
        UserOrganizationCentreLink.objects
        .filter(ORGANIZATION_ID_id=org_id, CENTRE_ID_id=centre_id)
        .values_list('USER_ID_id', flat=True)
    )

    if not user_ids:
        print("❌ No users linked to this org/centre")
        return

    users = MasterUser.objects.filter(USER_ID__in=user_ids)

    phones = [u.PHONE for u in users if u.SEND_SMS]
    emails = [u.EMAIL for u in users if u.SEND_EMAIL]

    message = f"INFO!! The temperature levels are back to normal for {dev_name}. No action is required - Regards Fertisense LLP"

    for phone in phones:
        send_sms(phone, message)

    if emails:
        send_email_notification("Alarm Normalized", message, emails)


# ================== Device Reading Log ==================
class DeviceReadingLog(models.Model):
    id = models.AutoField(primary_key=True)
    DEVICE_ID = models.IntegerField()
    SENSOR_ID = models.IntegerField()
    PARAMETER_ID = models.IntegerField()
    READING_DATE = models.DateField(auto_now_add=True)
    READING_TIME = models.TimeField(auto_now_add=True)
    READING = models.FloatField(null=True)
    ORGANIZATION_ID = models.IntegerField(null=True)
    CENTRE_ID = models.IntegerField(null=True)

    class Meta:
        db_table = "device_reading_log"

    def save(self, *args, **kwargs):
    # 🔹 Step 1: Log initiation
        start_time = datetime.now()
        print(f"🕒 [INITIATED] Device Reading Save started at: {start_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")

        if not self.READING_DATE:
            self.READING_DATE = timezone.now().date()
        if not self.READING_TIME:
            self.READING_TIME = timezone.now().time().replace(microsecond=0)

    # 🔹 Step 2: Save reading entry
        super().save(*args, **kwargs)

        insert_time = datetime.now()
        print(f"✅ [INSERT COMPLETED] DB entry saved at: {insert_time.strftime('%Y-%m-%d %H:%M:%S.%f')}")

    # ================== Fetch Parameter ==================
        from .models import MasterParameter, DeviceAlarmLog  # Avoid circular imports

        try:
            param = MasterParameter.objects.get(pk=self.PARAMETER_ID)
        except MasterParameter.DoesNotExist:
            print("❌ Parameter not found")
            return

        if self.READING is None:
            print("❌ No reading provided")
            return

    # 🔹 Step 3: Threshold check
        breached = (self.READING > param.UPPER_THRESHOLD or self.READING < param.LOWER_THRESHOLD)
        print(f"📡 Device {self.DEVICE_ID} Reading={self.READING}, Breach={breached}, Checked at {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")

        active_alarm = DeviceAlarmLog.objects.filter(
            DEVICE_ID=self.DEVICE_ID,
            SENSOR_ID=self.SENSOR_ID,
            PARAMETER_ID=self.PARAMETER_ID,
            IS_ACTIVE=1
        ).first()

    # 🔹 Step 4: Alarm creation
        if breached:
            if not active_alarm:
                alarm_start = datetime.now()
                print(f"🚨 [ALARM INITIATED] Creating new alarm at: {alarm_start.strftime('%Y-%m-%d %H:%M:%S.%f')}")

                DeviceAlarmLog.objects.create(
                    DEVICE_ID=self.DEVICE_ID,
                    SENSOR_ID=self.SENSOR_ID,
                    PARAMETER_ID=self.PARAMETER_ID,
                    READING=self.READING,
                    ORGANIZATION_ID=self.ORGANIZATION_ID or 1,
                    CENTRE_ID=self.CENTRE_ID,
                    CRT_DT=timezone.now().date(),
                    LST_UPD_DT=timezone.now().date(),
                    IS_ACTIVE=1
                )

                alarm_done = datetime.now()
                print(f"✅ [ALARM SAVED] Alarm record inserted at: {alarm_done.strftime('%Y-%m-%d %H:%M:%S.%f')}")
        else:
        # 🔹 Step 5: Alarm normalization
            if active_alarm:
                norm_start = datetime.now()
                print(f"✅ [NORMALIZATION INITIATED] at: {norm_start.strftime('%Y-%m-%d %H:%M:%S.%f')}")
                send_normalized_alert(active_alarm)

                active_alarm.IS_ACTIVE = 0
                active_alarm.LST_UPD_DT = timezone.now().date()
                active_alarm.save()

                norm_done = datetime.now()
                print(f"📧 [NORMALIZATION COMPLETED] at: {norm_done.strftime('%Y-%m-%d %H:%M:%S.%f')}")

                
                
                    # # Device ka naam fetch kar
                    # device = MasterDevice.objects.filter(DEVICE_ID=active_alarm.DEVICE_ID).first()
                    # devnm = device.DEVICE_NAME if device else f"Device {active_alarm.DEVICE_ID}"
                    # # 🔔 Send SMS + Email on normalization
                    # message = f"INFO!! The temperature levels are back to normal for {devnm}. No action is required - Regards Fertisense LLP"
                    # #print(msg)
                    # sms_ok = send_sms(TO_PHONE_NUMBER, message)   # <- apna number daalna
                    # mail_ok = send_email_notification("Alarm Normalized", message, "testwebservice71@gmail.com")

                    # # Agar dono me se koi bhi success hua toh DB me update
                    # if sms_ok or mail_ok:
                    #     DeviceAlarmLog.objects.filter(id=active_alarm.id).update(
                    #         NORMALIZED_SMS_DATE=now.date(),
                    #         NORMALIZED_SMS_TIME=now.time(),
                    #         NORMALIZED_EMAIL_DATE=now.date(),
                    #         NORMALIZED_EMAIL_TIME=now.time()
                    #         )
                    #     print("📌 NORMALIZED_SMS_DATE & NORMALIZED_SMS_TIME updated in DB")

        
    # def save(self, *args, **kwargs):
    #     # Automatically set date and time if not provided
    #     if not self.READING_DATE:
    #         self.READING_DATE = timezone.now().date()

    #     if not self.READING_TIME:
    #         #self.READING_TIME = timezone.now().time().replace(microsecond=0)
    #         self.READING_TIME = models.TimeField(auto_now_add=True)
    #         print("Reading Time-",self.READING_TIME)
    #     if self.READING is None:
    #         print("❌ Warning: READING is None")
    #     super().save(*args, **kwargs)

    #     try:
    #         param = MasterParameter.objects.get(pk=self.PARAMETER_ID)
    #     except MasterParameter.DoesNotExist:
    #         print("❌ Parameter not found")
    #         return

    #     if self.READING is None:
    #         print("❌ No reading provided")
    #         return

    #     breached = (self.READING > param.UPPER_THRESHOLD or self.READING < param.LOWER_THRESHOLD)
    #     print(f"📡 Device {self.DEVICE_ID} Reading={self.READING}, Breach={breached} timezone={datetime.now().astimezone().tzinfo},Current time{datetime.now()}")
      
    #     active_alarm = DeviceAlarmLog.objects.filter(
    #         DEVICE_ID=self.DEVICE_ID,
    #         SENSOR_ID=self.SENSOR_ID,
    #         PARAMETER_ID=self.PARAMETER_ID,
    #         IS_ACTIVE=1
    #     ).first()


    #     if breached:
    #         if not active_alarm:
    #             print("🚨 New Alarm Created")
    #             DeviceAlarmLog.objects.create(
    #                 DEVICE_ID=self.DEVICE_ID,
    #                 SENSOR_ID=self.SENSOR_ID,
    #                 PARAMETER_ID=self.PARAMETER_ID,
    #                 READING=self.READING,
    #                # ORG_ID=self.ORG_ID,
    #                 ORGANIZATION_ID=self.ORGANIZATION_ID or 1,
    #                 CENTRE_ID=self.CENTRE_ID,
    #                 CRT_DT=timezone.now().date(),
    #                 CRT_BY=self.CRT_BY or 1,
    #                 LST_UPD_DT=timezone.now().date(),
    #                 LST_UPD_BY=self.LST_UPD_BY or 1,
    #                 IS_ACTIVE=1
            
    #             )
    #     else:
    #         if active_alarm:
    #             updated = DeviceAlarmLog.objects.filter(
    #                 id=active_alarm.id
    #             ).update(
    #                 IS_ACTIVE=0,
    #                 NORMALIZED_DATE=timezone.now().date(),
    #                 NORMALIZED_TIME= datetime.now()

    #             )
    #             if updated:
    #                 print("✅ Alarm normalized")


    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)  # pehle reading save ho jaye

    # # Threshold check
    #     try:
    #         param = MasterParameter.objects.get(pk=self.PARAMETER_ID)
    #     except MasterParameter.DoesNotExist:
    #         return

    #     if self.READING is None:
    #         return

    # # Check breach
    #     if self.READING > param.UPPER_THRESHOLD or self.READING < param.LOWER_THRESHOLD:
    #     # 🔥 Pehle check kar - koi active alarm already open hai kya?
    #         existing_alarm = DeviceAlarmLog.objects.filter(
    #         DEVICE_ID=self.DEVICE_ID,
    #         SENSOR_ID=self.SENSOR_ID,
    #         PARAMETER_ID=self.PARAMETER_ID,
    #         IS_ACTIVE=True
    #     ).exists()

    #     if not existing_alarm:
    #         # Naya alarm banao
    #         DeviceAlarmLog.objects.create(
    #             DEVICE_ID=self.DEVICE_ID,
    #             SENSOR_ID=self.SENSOR_ID,
    #             PARAMETER_ID=self.PARAMETER_ID,
    #             ALARM_DATE=self.READING_DATE,
    #             ALARM_TIME=self.READING_TIME,
    #             READING=self.READING,
    #             ORG_ID=self.ORG_ID,
    #             UNIT_ID=self.UNIT_ID,
    #             CRT_DT=timezone.now().date(),
    #             CRT_BY=self.CRT_BY or 1,
    #             LST_UPD_DT=timezone.now().date(),
    #             LST_UPD_BY=self.LST_UPD_BY or 1,
    #             DEVICE_ALARM_LOG_VER=self.DEVICE_READING_LOG_VER,
    #             CHANNEL=self.CHANNEL,
    #             CHANNEL_CD=self.CHANNEL_CD,
    #             IS_ACTIVE=True   # active alarm
    #         )

        #     # Email notification
        #     send_mail(
        #         subject=f'Alarm! {param.PARAMETER_NAME} threshold crossed',
        #         message=f'Device {self.DEVICE_ID} reading {self.READING} crossed limits ({param.LOWER_THRESHOLD}-{param.UPPER_THRESHOLD})',
        #         from_email='iot@yourdomain.com',
        #         recipient_list=['admin@yourdomain.com'],
        #         fail_silently=True,
        #     )

        #     # SMS notification
        #     send_sms(
        #         to_number='+917355383021',
        #         message=f'ALERT! Device {self.DEVICE_ID} {param.PARAMETER_NAME}={self.READING} crossed ({param.LOWER_THRESHOLD}-{param.UPPER_THRESHOLD})'
        #     )

    #else:
        # 🔥 Agar value normal aa gayi toh active alarm close kar do
    #        DeviceAlarmLog.objects.filter(
    #        DEVICE_ID=self.DEVICE_ID,
    #        SENSOR_ID=self.SENSOR_ID,
    #        PARAMETER_ID=self.PARAMETER_ID,
    #        IS_ACTIVE=True
  #      ).update(IS_ACTIVE=False, NORMALIZED_DATE=self.READING_DATE, NORMALIZED_TIME=self.READING_TIME)


class CompassDates(models.Model):
    ORGANIZATION_ID = models.IntegerField()
    BRANCH_ID = models.IntegerField() 
    CMPS_DT = models.DateField(null=True, blank=True) 
    class Meta: 
        db_table = 'compass_dates' 
        unique_together = (('ORGANIZATION_ID', 'BRANCH_ID'),) 
        
class MasterDevice(models.Model): 
    DEVICE_MACID =models.CharField(max_length=100,null=True,blank=True) 
    CENTRE_ID = models.IntegerField(default=1) 
    DEVICE_ID = models.AutoField(primary_key=True) 
    DEVICE_NAME = models.CharField(max_length=200) 
    CATEGORY_ID = models.IntegerField(null=True,blank=True)
    DEVICE_MNEMONIC = models.CharField(max_length=20, null=True, blank=True) 
    DEVICE_IP = models.CharField(max_length=30, null=True, blank=True) 
    DEVICE_STATUS = models.IntegerField(default=1) 
    DEVICE_STATUS_CD = models.IntegerField(default=1) 
    ORGANIZATION_ID = models.IntegerField() 
    CENTRE_ID = models.IntegerField() 
    CRT_DT = models.DateField(null=True, blank=True) 
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True) 
    LST_UPD_BY = models.IntegerField(null=True, blank=True) 
    
    class Meta: db_table = 'master_device'

from django.db import models

# -------------------------
# 1️⃣ Master Organization
# -------------------------
class MasterOrganization(models.Model):
    ORGANIZATION_ID = models.AutoField(primary_key=True)
    ORGANIZATION_NAME = models.CharField(max_length=200)
    ORGANIZATION_STATUS = models.IntegerField(default=1)
    ORGANIZATION_STATUS_CD = models.IntegerField(default=1)
    CENTRE_ID = models.IntegerField()
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    MASTER_ORGANIZATION_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.ORGANIZATION_NAME

# -------------------------
# 2️⃣ Master Parameter
# -------------------------
class MasterParameter(models.Model):
    PARAMETER_ID = models.AutoField(primary_key=True)
    PARAMETER_NAME = models.CharField(max_length=200)
    UPPER_THRESHOLD = models.FloatField(null=True, blank=True)
    LOWER_THRESHOLD = models.FloatField(null=True, blank=True)
    THRESHOLD = models.FloatField(null=True, blank=True)
    UOM_ID = models.IntegerField(null=True, blank=True)
    PARAMETER_STATUS = models.IntegerField(default=1)
    PARAMETER_STATUS_CD = models.IntegerField(default=1)
    ORGANIZATION_ID = models.IntegerField()
    CENTRE_ID = models.IntegerField()
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    MASTER_PARAMETER_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.PARAMETER_NAME

# -------------------------
# 3️⃣ Master Sensor
# -------------------------
class MasterSensor(models.Model):
    SENSOR_ID = models.AutoField(primary_key=True)
    SENSOR_NAME = models.CharField(max_length=200)
    SENSOR_TYPE = models.CharField(null=True,max_length=100)
    SENSOR_STATUS = models.IntegerField(default=1)
    SENSOR_STATUS_CD = models.IntegerField(default=1)
    ORGANIZATION_ID = models.IntegerField()
    CENTRE_ID = models.IntegerField()
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    MASTER_SENSOR_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.SENSOR_NAME

# -------------------------
# 4️⃣ SE User
# -------------------------
class SeUser(models.Model):
    USER_ID = models.AutoField(primary_key=True)
    USER_NAME = models.CharField(max_length=250)
    ROLE_ID= models.IntegerField(null=True)
    LOGIN_ID = models.CharField(max_length=20)
    USER_PASSWORD = models.CharField(max_length=20)
    DB_DRIVER = models.CharField(max_length=35)
    DB_URL = models.CharField(max_length=50)
    DB_UNAME = models.CharField(max_length=20)
    DB_PASSWORD = models.CharField(max_length=20)

    def __str__(self):
        return self.USER_NAME

# -------------------------
# 5️⃣ Sensor Parameter Link
# -------------------------
class SensorParameterLink(models.Model):
    SENSOR_ID = models.IntegerField()
    PARAMETER_ID = models.IntegerField()
    ORGANIZATION_ID = models.IntegerField()
    CENTRE_ID = models.IntegerField()
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    SENSOR_PARAMETER_LINK_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('SENSOR_ID', 'PARAMETER_ID')

# -------------------------
# 6️⃣ Device Sensor Link
# -------------------------
class DeviceSensorLink(models.Model):
    DEVICE_ID = models.IntegerField()
    SENSOR_ID = models.IntegerField()
    ORGANIZATION_ID = models.IntegerField()
    CENTRE_ID = models.IntegerField()
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    DEVICE_SENSOR_LINK_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('DEVICE_ID', 'SENSOR_ID')

# -------------------------
# 7️⃣ Device Alarm Call Log
# -------------------------
class DeviceAlarmCallLog(models.Model):
    DEVICE_ID = models.IntegerField()
    SENSOR_ID = models.IntegerField()
    PARAMETER_ID = models.IntegerField()
    ALARM_DATE = models.DateField()
    ALARM_TIME = models.TimeField()
    PHONE_NUM = models.IntegerField()
    CALL_DATE = models.DateField()
    CALL_TIME = models.IntegerField()
    SMS_CALL_FLAG = models.IntegerField()
    REMARKS = models.CharField(max_length=200, null=True, blank=True)
    ORGANIZATION_ID = models.IntegerField()
    CENTRE_ID = models.IntegerField()
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    DEVICE_ALARM_CALL_LOG_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = (
            'DEVICE_ID','SENSOR_ID','PARAMETER_ID','ALARM_DATE','ALARM_TIME',
            'PHONE_NUM','CALL_DATE','CALL_TIME','SMS_CALL_FLAG'
        )

# -------------------------
# 8️⃣ Device Alarm Log
# -------------------------
class DeviceAlarmLog(models.Model):
    DEVICE_ID = models.IntegerField()
    SENSOR_ID = models.IntegerField()
    PARAMETER_ID = models.IntegerField()
    ALARM_DATE = models.DateField(auto_now_add=True)   # record create hone par date
    ALARM_TIME = models.TimeField(auto_now_add=True) 
    READING = models.FloatField(null=True, blank=True)
    NORMALIZED_DATE = models.DateField(null=True, blank=True)
    NORMALIZED_TIME=models.TimeField(null=True,blank=True)
    SMS_DATE = models.DateField(null=True, blank=True)
    SMS_TIME = models.TimeField(null=True, blank=True)
    EMAIL_DATE = models.DateField(null=True, blank=True)
    EMAIL_TIME = models.TimeField(null=True, blank=True)
    NORMALIZED_SMS_DATE = models.DateField(null=True, blank=True)
    NORMALIZED_SMS_TIME = models.TimeField(null=True, blank=True)
    NORMALIZED_EMAIL_DATE = models.DateField(null=True, blank=True)
    NORMALIZED_EMAIL_TIME = models.TimeField(null=True, blank=True)
    ORGANIZATION_ID = models.IntegerField(default=1)
    CENTRE_ID = models.IntegerField()
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    DEVICE_ALARM_LOG_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)
        # 🔥 New field
    IS_ACTIVE = models.IntegerField(default=1)

    class Meta:
        unique_together = ('DEVICE_ID','SENSOR_ID','PARAMETER_ID','ALARM_DATE','ALARM_TIME')
        

from django.db import models

class MasterUOM(models.Model):
    UOM_ID = models.AutoField(primary_key=True)   # Auto increment ID
    UOM_NAME = models.CharField(max_length=200, unique=True)  # Unit name (unique to avoid duplicates)
    UOM_STATUS = models.BooleanField(default=True)  # Active / Inactive
    CRT_DT = models.DateTimeField(auto_now_add=True)  # Automatically created date
    CRT_BY = models.IntegerField(null=True, blank=True)  # Created by (user ID)

    class Meta:
        db_table = 'master_uom'   # Explicit table name
        verbose_name = "Unit of Measurement"
        verbose_name_plural = "Units of Measurement"

    def __str__(self):
        return self.UOM_NAME

from django.db import models

class MasterCentre(models.Model):
    CENTRE_ID = models.AutoField(primary_key=True)
    CENTRE_NAME = models.CharField(max_length=200)
    CENTRE_STATUS = models.IntegerField(default=1)
    CENTRE_STATUS_CD = models.IntegerField(default=1)
    ORGANIZATION_ID = models.IntegerField()   # Kis organization ke andar centre hai
    CRT_DT = models.DateField(null=True, blank=True)
    CRT_BY = models.IntegerField(null=True, blank=True)
    LST_UPD_DT = models.DateField(null=True, blank=True)
    LST_UPD_BY = models.IntegerField(null=True, blank=True)
    MASTER_CENTRE_VER = models.TextField(null=True, blank=True)
    CHANNEL = models.IntegerField(null=True, blank=True)
    CHANNEL_CD = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.CENTRE_NAME
    
    
    
from django.db import models

class MasterRole(models.Model):
     ROLE_ID = models.AutoField(primary_key=True)
     ROLE_NAME = models.CharField(max_length=100)

class Meta:
        db_table = "master_role"

def __str__(self):
        return self.ROLE_NAME

from django.db import models

class CentreOrganizationLink(models.Model):

    ORGANIZATION_ID = models.IntegerField()
    CENTRE_ID = models.IntegerField()

    class Meta:
        unique_together = ('ORGANIZATION_ID', 'CENTRE_ID')

class MasterUser(models.Model):

    USER_ID = models.AutoField(primary_key=True)  # Auto increment PK
    USERNAME = models.CharField(max_length=50, unique=True)
    PASSWORD = models.CharField(max_length=255)   # Password hash store karo
    ACTUAL_NAME = models.CharField(max_length=100)
    ROLE_ID = models.IntegerField(null=True)
    PHONE= models.CharField(null=True,max_length=100)
    SEND_SMS = models.IntegerField(null=True)
    EMAIL = models.EmailField(unique=True)
    SEND_EMAIL =models.IntegerField(null=True)
    CREATED_BY = models.IntegerField(null=True, blank=True)  # Reference to another USER_ID if needed
    CREATED_ON = models.DateTimeField(auto_now_add=True)     # Auto timestamp
    VALIDITY_START = models.DateField(null=True, blank=True)
    VALIDITY_END = models.DateField(null=True, blank=True)
    PASSWORD_RESET = models.BooleanField(default=False)

    class Meta:
        db_table = "master_user"
    
    def __str__(self):
        return self.USERNAME
    


class UserOrganizationCentreLink(models.Model):
    USER_ID = models.ForeignKey("MasterUser", on_delete=models.CASCADE)
    ORGANIZATION_ID = models.ForeignKey("MasterOrganization", on_delete=models.CASCADE)
    CENTRE_ID = models.ForeignKey("MasterCentre", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.USER.USERNAME} → {self.ORGANIZATION.ORGANIZATION_NAME} → {self.CENTRE.CENTRE_NAME}"
    
    class Meta:
        db_table = "userorganizationcentrelink"


class MasterNotificationTime(models.Model):
    ORGANIZATION_ID =models.IntegerField()
    NOTIFICATION_TIME = models.IntegerField(help_text="Notification time in seconds")

    class Meta:
        db_table = 'master_notification_time'


class DeviceCategory(models.Model):
    CATEGORY_ID =models.AutoField(primary_key=True)
    CATEGORY_NAME =models.CharField(max_length=100)

    class Meta:
        db_table = 'device_category'
