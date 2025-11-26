# iot_api/models.py
from django.db import models
from django.utils import timezone
from datetime import datetime
import requests
from django.core.mail import send_mail
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import pytz
from django.utils import timezone

# device_name =""
dev_reading =""
upth =""
lowth=""
currentreading = ""

# ================== SMS Config ==================
SMS_API_URL = "https://www.universalsmsadvertising.com/universalsmsapi.php"
SMS_USER = "8960853914"
SMS_PASS = "8960853914"
SENDER_ID = "FRTLLP"

# # ================== EMAIL CONFIG ==================
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'testwebservice71@gmail.com'
# EMAIL_HOST_PASSWORD = 'akuu vulg ejlg ysbt'  # Gmail app password

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
def send_email_brevo(to_email, subject, html_content):
    print("📧 Sending Email via Brevo...")

    BREVO_API_KEY = os.getenv("BREVO_API_KEY")   # <--- NO HARD CODE
    if not BREVO_API_KEY:
        print("❌ ERROR: BREVO_API_KEY not found in environment variables!")
        return
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email}],
            sender={"email": "fertisenseiot@gmail.com", "name": "Fertisense"},
            subject=subject,
            html_content=html_content
        )

        response = api_instance.send_transac_email(email)
        print("✔ Email sent:", response)

    except ApiException as e:
        print("❌ Email failed:", e)    


IST = pytz.timezone("Asia/Kolkata")  # ✅ IST timezone

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

    # for phone in phones:
    #     send_sms(phone, message)

    # ---- Normalize, split, strip, deduplicate ----
    unique_phones = set()

    for p in phones:
        if p:  # ignore None or empty values
            for num in p.split(","):
                num = num.strip()
                if num:
                    unique_phones.add(num)

    print("Unique phone numbers:", unique_phones)

    # ---- Send SMS to each unique phone number ----
    for phone in unique_phones:
        send_sms(phone, message)

    if emails:
        subject = f"Device {dev_name}'s reading is now in acceptable range"

    html_content = f"""
        <h2>Device Reading Normalized</h2>
        <p><strong>Device:</strong> {dev_name}</p>
        <p>The device's readings have now returned to a normal acceptable range.</p>
        <p>Regards,<br>Fertisense IoT Monitoring System</p>
    """

    for em in emails:
        send_email_brevo(em, subject, html_content)



# ================== Device Reading Log ==================
class DeviceReadingLog(models.Model):
    id = models.AutoField(primary_key=True)
    DEVICE_ID = models.IntegerField()
    SENSOR_ID = models.IntegerField()
    PARAMETER_ID = models.IntegerField()
    READING_DATE = models.DateField(null=True, blank=True)
    READING_TIME = models.TimeField(null=True, blank=True)
    READING = models.FloatField(null=True)
    ORGANIZATION_ID = models.IntegerField(null=True)
    CENTRE_ID = models.IntegerField(null=True)

    class Meta:
        db_table = "device_reading_log"

    def save(self, *args, **kwargs):
        from .models import MasterParameter, DeviceAlarmLog

        # 🔹 IST datetime
        now_dt = timezone.now().astimezone(IST)
        norm_date = now_dt.date()
        norm_time = now_dt.time().replace(microsecond=0)

        # 🔹 Step 1: Set reading date/time if not provided
        if not self.READING_DATE:
            self.READING_DATE = norm_date
        if not self.READING_TIME:
            self.READING_TIME = norm_time

        # 🔹 Step 2: Save reading entry
        super().save(*args, **kwargs)

        # 🔹 Step 3: Fetch parameter
        try:
            param = MasterParameter.objects.get(pk=self.PARAMETER_ID)
        except MasterParameter.DoesNotExist:
            print("❌ Parameter not found")
            return

        if self.READING is None:
            print("❌ No reading provided")
            return
        

        breached = (self.READING > param.UPPER_THRESHOLD or self.READING < param.LOWER_THRESHOLD)
        
        # 🔹 Step 4: Check for active alarm
        active_alarm = DeviceAlarmLog.objects.filter(
            DEVICE_ID=self.DEVICE_ID,
            SENSOR_ID=self.SENSOR_ID,
            PARAMETER_ID=self.PARAMETER_ID,
            IS_ACTIVE=1
        ).first()
        print("breached value",breached)
        # 🔹 Step 5: Handle breached alarm
        if breached:
            if not active_alarm:
                DeviceAlarmLog.objects.create(
                    DEVICE_ID=self.DEVICE_ID,
                    SENSOR_ID=self.SENSOR_ID,
                    PARAMETER_ID=self.PARAMETER_ID,
                    READING=self.READING,
                    ORGANIZATION_ID=self.ORGANIZATION_ID or 1,
                    CENTRE_ID=self.CENTRE_ID,
                    CRT_DT=norm_date,
                    LST_UPD_DT=norm_date,
                    SMS_DATE=None,
                    SMS_TIME=None,
                    EMAIL_DATE=None,
                    EMAIL_TIME=None,
                    IS_ACTIVE=1
                    
                )
                print(f"🚨 New Alarm created for device {self.DEVICE_ID}")
        else:
            # 🔹 Step 6: Handle normalized alarm
            if active_alarm:
                print(f"✅ Alarm normalized for device {self.DEVICE_ID}, sending notifications...")
                send_normalized_alert(active_alarm)
                print(f"✅ Alarm normalized for device {self.DEVICE_ID}, sending Email notifications...")
                # send_email_notification(active_alarm)

                # 🔹 Update all normalized timestamps in IST
                active_alarm.IS_ACTIVE = 0
                active_alarm.LST_UPD_DT = norm_date
                active_alarm.NORMALIZED_DATE = norm_date
                active_alarm.NORMALIZED_TIME = norm_time
                active_alarm.NORMALIZED_SMS_DATE = norm_date
                active_alarm.NORMALIZED_SMS_TIME = norm_time
                active_alarm.NORMALIZED_EMAIL_DATE = norm_date
                active_alarm.NORMALIZED_EMAIL_TIME = norm_time
                active_alarm.save()
                print(f"📧 Normalization timestamps updated for device {self.DEVICE_ID}")
                

# # ================== Alarm Normalized Alert ==================
# import pytz

# IST = pytz.timezone("Asia/Kolkata")
# now_dt = timezone.now().astimezone(IST)  # ✅ Convert UTC -> IST

# def send_normalized_alert(active_alarm):
#     from .models import MasterDevice, UserOrganizationCentreLink, MasterUser  # Import here to avoid circular imports

#     device = MasterDevice.objects.filter(DEVICE_ID=active_alarm.DEVICE_ID).first()
#     if not device:
#         print("❌ Device not found")
#         return

#     dev_name = device.DEVICE_NAME
#     org_id = device.ORGANIZATION_ID
#     centre_id = device.CENTRE_ID

#     user_ids = list(
#         UserOrganizationCentreLink.objects
#         .filter(ORGANIZATION_ID_id=org_id, CENTRE_ID_id=centre_id)
#         .values_list('USER_ID_id', flat=True)
#     )

#     if not user_ids:
#         print("❌ No users linked to this org/centre")
#         return

#     users = MasterUser.objects.filter(USER_ID__in=user_ids)

#     phones = [u.PHONE for u in users if u.SEND_SMS]
#     emails = [u.EMAIL for u in users if u.SEND_EMAIL]

#     message = f"INFO!! The temperature levels are back to normal for {dev_name}. No action is required - Regards Fertisense LLP"

#     for phone in phones:
#         send_sms(phone, message)

#     if emails:
#         send_email_notification("Alarm Normalized", message, emails)


# # ================== Device Reading Log ==================
# class DeviceReadingLog(models.Model):
#     id = models.AutoField(primary_key=True)
#     DEVICE_ID = models.IntegerField()
#     SENSOR_ID = models.IntegerField()
#     PARAMETER_ID = models.IntegerField()
#     READING_DATE = models.DateField(auto_now_add=True)
#     READING_TIME = models.TimeField(auto_now_add=True)
#     READING = models.FloatField(null=True)
#     ORGANIZATION_ID = models.IntegerField(null=True)
#     CENTRE_ID = models.IntegerField(null=True)

#     class Meta:
#         db_table = "device_reading_log"

#     def save(self, *args, **kwargs):
#         from .models import MasterParameter, DeviceAlarmLog  # Avoid circular imports
#         from django.utils import timezone
#         now_dt = timezone.now()

#     # 🔹 Step 1: Set reading date/time
#         if not self.READING_DATE:
#             self.READING_DATE = now_dt.date()
#         if not self.READING_TIME:
#             self.READING_TIME = now_dt.time().replace(microsecond=0)

#     # 🔹 Step 2: Save reading entry
#         super().save(*args, **kwargs)

#     # 🔹 Step 3: Fetch parameter
#         try:
#             param = MasterParameter.objects.get(pk=self.PARAMETER_ID)
#         except MasterParameter.DoesNotExist:
#             print("❌ Parameter not found")
#             return

#         if self.READING is None:
#             print("❌ No reading provided")
#             return

#         breached = (self.READING > param.UPPER_THRESHOLD or self.READING < param.LOWER_THRESHOLD)

#     # 🔹 Step 4: Check for active alarm
#         active_alarm = DeviceAlarmLog.objects.filter(
#             DEVICE_ID=self.DEVICE_ID,
#             SENSOR_ID=self.SENSOR_ID,
#             PARAMETER_ID=self.PARAMETER_ID,
#             IS_ACTIVE=1
#         ).first()

#     # 🔹 Step 5: Handle breached alarm
#         if breached:
#             if not active_alarm:
#             # Create new alarm if breached and no active alarm
#                 DeviceAlarmLog.objects.create(
#                     DEVICE_ID=self.DEVICE_ID,
#                     SENSOR_ID=self.SENSOR_ID,
#                     PARAMETER_ID=self.PARAMETER_ID,
#                     READING=self.READING,
#                     ORGANIZATION_ID=self.ORGANIZATION_ID or 1,
#                     CENTRE_ID=self.CENTRE_ID,
#                     CRT_DT=now_dt.date(),
#                     LST_UPD_DT=now_dt.date(),
#                     IS_ACTIVE=1
#                 )
#                 print(f"🚨 New Alarm created for device {self.DEVICE_ID}")
#         else:
#         # 🔹 Step 6: Handle normalized alarm
#             if active_alarm:
#                 print(f"✅ Alarm normalized for device {self.DEVICE_ID}, sending notifications...")
#                 send_normalized_alert(active_alarm)

#             # Update all normalized timestamps in DB
#                 active_alarm.IS_ACTIVE = 0
#                 active_alarm.LST_UPD_DT = now_dt.date()
#                 active_alarm.NORMALIZED_DATE = now_dt.date()
#                 active_alarm.NORMALIZED_TIME = now_dt.time().replace(microsecond=0)
#                 active_alarm.NORMALIZED_SMS_DATE = now_dt.date()
#                 active_alarm.NORMALIZED_SMS_TIME = now_dt.time().replace(microsecond=0)
#                 active_alarm.NORMALIZED_EMAIL_DATE = now_dt.date()
#                 active_alarm.NORMALIZED_EMAIL_TIME = now_dt.time().replace(microsecond=0)
            
#                 active_alarm.save()
#                 print(f"📧 Normalization timestamps updated for device {self.DEVICE_ID}") 

# ================== Alarm Normalized Alert ==================
# import pytz

# IST = pytz.timezone("Asia/Kolkata")  # ✅ IST timezone

# def send_normalized_alert(active_alarm):
#     from .models import MasterDevice, UserOrganizationCentreLink, MasterUser

#     device = MasterDevice.objects.filter(DEVICE_ID=active_alarm.DEVICE_ID).first()
#     if not device:
#         print("❌ Device not found")
#         return

#     dev_name = device.DEVICE_NAME
#     org_id = device.ORGANIZATION_ID
#     centre_id = device.CENTRE_ID

#     user_ids = list(
#         UserOrganizationCentreLink.objects
#         .filter(ORGANIZATION_ID_id=org_id, CENTRE_ID_id=centre_id)
#         .values_list('USER_ID_id', flat=True)
#     )

#     if not user_ids:
#         print("❌ No users linked to this org/centre")
#         return

#     users = MasterUser.objects.filter(USER_ID__in=user_ids)

#     phones = [str(u.PHONE).strip() for u in users if u.SEND_SMS]
#     emails = [u.EMAIL for u in users if u.SEND_EMAIL]

#     message = f"INFO!! The temperature levels are back to normal for {dev_name}. No action is required - Regards Fertisense LLP"

#     for phone in phones:
#         if phone:
#             # send_sms(",".join(phones), message)
#             print("starting to send_sms")
#             send_sms(phone, message)
#             print("send_sms completed") 
#     if emails:
#         send_email_notification("Alarm Normalized", message, emails)


# # ================== Device Reading Log ==================
# class DeviceReadingLog(models.Model):
#     id = models.AutoField(primary_key=True)
#     DEVICE_ID = models.IntegerField()
#     SENSOR_ID = models.IntegerField()
#     PARAMETER_ID = models.IntegerField()
#     READING_DATE = models.DateField(null=True, blank=True)
#     READING_TIME = models.TimeField(null=True, blank=True)
#     READING = models.FloatField(null=True)
#     ORGANIZATION_ID = models.IntegerField(null=True)
#     CENTRE_ID = models.IntegerField(null=True)

#     class Meta:
#         db_table = "device_reading_log"

# def save(self, *args, **kwargs):
#     from .models import MasterParameter, DeviceAlarmLog

#     # 🔹 IST datetime
#     now_dt = timezone.now().astimezone(IST)
#     norm_date = now_dt.date()
#     norm_time = now_dt.time().replace(microsecond=0)

#     # --- Step 1: Reading Date ---
#     if not self.READING_DATE:
#         self.READING_DATE = now_dt.date()

#     # --- Step 2: Reading Time ---
#     if not self.READING_TIME:
#         self.READING_TIME = now_dt.time()
#     else:
#         if self.READING_TIME.microsecond == 0:
#             self.READING_TIME = self.READING_TIME.replace(
#                 microsecond=now_dt.microsecond
#             )

#     # 🔹 Save reading record
#     super().save(*args, **kwargs)

#     # --- Fetch Parameter ---
#     try:
#         param = MasterParameter.objects.get(pk=self.PARAMETER_ID)
#     except MasterParameter.DoesNotExist:
#         print("❌ Parameter not found")
#         return

#     if self.READING is None:
#         print("❌ No reading provided")
#         return

#     breached = (
#         self.READING > param.UPPER_THRESHOLD or
#         self.READING < param.LOWER_THRESHOLD
#     )

#     # --- Use device timestamps for alarms ---
#     device_date = self.READING_DATE or norm_date
#     device_time = self.READING_TIME or norm_time

#     # 🔹 Check for active alarm
#     active_alarm = DeviceAlarmLog.objects.filter(
#         DEVICE_ID=self.DEVICE_ID,
#         SENSOR_ID=self.SENSOR_ID,
#         PARAMETER_ID=self.PARAMETER_ID,
#         IS_ACTIVE=1
#     ).first()

#     print("breached value", breached)

#     # ----------------------------------------------------------------------
#     # 🚨 Case 1: READING Breached
#     # ----------------------------------------------------------------------
#     if breached:
#         if not active_alarm:
#             DeviceAlarmLog.objects.create(
#                 DEVICE_ID=self.DEVICE_ID,
#                 SENSOR_ID=self.SENSOR_ID,
#                 PARAMETER_ID=self.PARAMETER_ID,
#                 READING=self.READING,
#                 ORGANIZATION_ID=self.ORGANIZATION_ID or 1,
#                 CENTRE_ID=self.CENTRE_ID,
#                 CRT_DT=device_date,
#                 LST_UPD_DT=device_date,
#                 IS_ACTIVE=1
#             )
#             print(f"🚨 New Alarm created for device {self.DEVICE_ID}")
#         return

#     # ----------------------------------------------------------------------
#     # ✅ Case 2: READING Normalized
#     # ----------------------------------------------------------------------
#     if active_alarm:
#         print(f"✅ Alarm normalized for device {self.DEVICE_ID}, sending notifications...")

#         send_normalized_alert(active_alarm)

#         active_alarm.IS_ACTIVE = 0
#         active_alarm.LST_UPD_DT = device_date


#         active_alarm.NORMALIZED_DATE = device_date
#         active_alarm.NORMALIZED_TIME = device_time

#         active_alarm.NORMALIZED_SMS_DATE = device_date
#         active_alarm.NORMALIZED_SMS_TIME = device_time

#         active_alarm.NORMALIZED_EMAIL_DATE = device_date
#         active_alarm.NORMALIZED_EMAIL_TIME = device_time

#         active_alarm.save()
#         print(f"📧 Normalization updated for device {self.DEVICE_ID}")





    # def save(self, *args, **kwargs):
    #     if not self.READING_DATE:
    #         self.READING_DATE = timezone.now().date()
    #     # Ensure READING_TIME is set
    #     if not self.READING_TIME:
    #         self.READING_TIME = timezone.now().time().replace(microsecond=0)
    #     super().save(*args, **kwargs)  # Save reading first

    #     # ================== Fetch Parameter ==================
    #     from .models import MasterParameter, DeviceAlarmLog  # Avoid circular imports

    #     try:
    #         param = MasterParameter.objects.get(pk=self.PARAMETER_ID)
    #     except MasterParameter.DoesNotExist:
    #         print("❌ Parameter not found")
    #         return

    #     if self.READING is None:
    #         print("❌ No reading provided")
    #         return

    #     breached = (self.READING > param.UPPER_THRESHOLD or self.READING < param.LOWER_THRESHOLD)
    #     print(f"📡 Device {self.DEVICE_ID} Reading={self.READING}, Breach={breached}, Time={datetime.now()}")

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
    #                 ORGANIZATION_ID=self.ORGANIZATION_ID or 1,
    #                 CENTRE_ID=self.CENTRE_ID,
    #                 CRT_DT=timezone.now().date(),
    #                 LST_UPD_DT=timezone.now().date(),
    #                 IS_ACTIVE=1
    #             )
    #     else:
    #         if active_alarm:
    #             print("✅ Alarm normalized. Sending notifications...")
    #             send_normalized_alert(active_alarm)
    #             # Update alarm as inactive
    #             active_alarm.IS_ACTIVE = 0
    #             active_alarm.LST_UPD_DT = timezone.now().date()
    #             active_alarm.save()
                
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
    class Meta:
        db_table = "iot_api_masterdevice"   # ⭐⭐ EXACT TABLE NAME ⭐⭐

from django.db import models

# -------------------------
# 1️⃣ Master Organization
# -------------------------
class MasterOrganization(models.Model):
    ORGANIZATION_ID = models.AutoField(primary_key=True)
    ORGANIZATION_NAME = models.CharField(max_length=200)
    ORGANIZATION_STATUS = models.IntegerField(default=1)
    ORGANIZATION_STATUS_CD = models.IntegerField(default=1)
    CENTRE_ID = models.IntegerField(null=True, blank=True)
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
    ORGANIZATION_ID = models.IntegerField(null=True,blank=True)
    CENTRE_ID = models.IntegerField(null=True,blank=True)
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
    ORGANIZATION_ID = models.IntegerField(null=True,blank=True)
    CENTRE_ID = models.IntegerField(null=True,blank=True)
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
    ORGANIZATION_ID = models.IntegerField(null=True,blank=True)
    CENTRE_ID = models.IntegerField(null=True,blank=True)
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
    ORGANIZATION_ID = models.IntegerField(null=True,blank=True)
    CENTRE_ID = models.IntegerField(null=True,blank=True)
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
    CENTRE_ID = models.IntegerField(null=True , blank=True)
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
        db_table = "devicealarmlog"
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
    EMAIL = models.EmailField(null=True,max_length=500)
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
    created_by = models.IntegerField(null=True, blank=True)    

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

class MasterSubscriptionInfo(models.Model):
    Subscription_ID = models.AutoField(primary_key=True)
    Package_Name = models.CharField(max_length=500)
    CRT_date = models.DateTimeField(null=True, blank=True)
    CRT_BY = models.CharField(max_length=45, null=True, blank=True)

    class Meta:
        db_table = 'Master_Subscription_Info'
        verbose_name = 'Master Subscription Info'
        verbose_name_plural = 'Master Subscription Infos'

    def __str__(self):
        return self.Package_Name    
    
class Master_Plan_Type(models.Model):
    Plan_ID = models.AutoField(primary_key=True)
    Plan_Name = models.CharField(max_length=500)

    class Meta:
        db_table = 'Master_Plan_Type'


from datetime import date, timedelta
from django.db import models, transaction
from datetime import date
from django.db import models, transaction

class SubscriptionHistory(models.Model):
    STATUS_CHOICES = (
        ('Future', 'Future'),   # Scheduled subscription
        ('Active', 'Active'),   # Currently active
        ('Expired', 'Expired'), # Already ended
    )

    id = models.AutoField(primary_key=True)
    Device_ID = models.IntegerField()
    Subscription_Start_date = models.DateField()
    Subcription_End_date = models.DateField(null=True, blank=True)
    Subscription_ID = models.IntegerField(null=True, blank=True)
    Plan_ID = models.IntegerField(null=True, blank=True)
    Payment_Date = models.DateField(null=True, blank=True)
    Status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Future')

    class Meta:
        db_table = 'Subcription_History'
        unique_together = ('Device_ID', 'Subscription_Start_date')
        verbose_name = 'Subscription History'
        verbose_name_plural = 'Subscription Histories'

    def __str__(self):
        return f"Device {self.Device_ID} | {self.Status} | Start {self.Subscription_Start_date}"
    def save(self, *args, **kwargs): today = date.today() # 1️⃣ Decide status based on dates if self.Subcription_End_date and self.Subcription_End_date < today: self.Status = 'Expired' elif self.Subscription_Start_date > today: self.Status = 'Future' else: self.Status = 'Active' with transaction.atomic(): # 2️⃣ Adjust other subscriptions for same device overlaps = SubscriptionHistory.objects.filter(Device_ID=self.Device_ID).exclude(pk=self.pk) for o in overlaps: o_today_status = None # Expire if end date passed if o.Subcription_End_date and o.Subcription_End_date < today: o.Status = 'Expired' # Future → Active if start date reached elif o.Subscription_Start_date <= today and (not o.Subcription_End_date or o.Subcription_End_date >= today): o.Status = 'Active' # Otherwise future elif o.Subscription_Start_date > today: o.Status = 'Future' o.save() super().save(*args, **kwargs)

def save(self, *args, **kwargs):
    today = date.today()

    # 1️⃣ Decide status of current subscription
    if self.Subcription_End_date and self.Subcription_End_date < today:
        self.Status = 'Expired'
    elif self.Subscription_Start_date > today:
        self.Status = 'Future'
    else:
        self.Status = 'Active'

    super().save(*args, **kwargs)  # Save current first

    # 2️⃣ Update other subscriptions WITHOUT calling their save()
    overlaps = SubscriptionHistory.objects.filter(Device_ID=self.Device_ID).exclude(pk=self.pk)

    for o in overlaps:
        if o.Subcription_End_date and o.Subcription_End_date < today:
            new_status = 'Expired'
        elif o.Subscription_Start_date > today:
            new_status = 'Future'
        else:
            new_status = 'Expired'   # OLD subscriptions should NEVER be active

        SubscriptionHistory.objects.filter(pk=o.pk).update(Status=new_status)


class DeviceStatusAlarmLog(models.Model):
    DEVICE_STATUS_ALARM_ID = models.AutoField(primary_key=True)
    DEVICE_ID = models.IntegerField()

    # Scrap / active device flag
    # 1 = device exists / active, 0 = device scrap
    DEVICE_STATUS = models.IntegerField(default=1)

    # Alarm for online/offline
    # 1 = offline alarm active, 0 = normalized (device online now)
    IS_ACTIVE = models.IntegerField(default=1)

    CREATED_ON_DATE = models.DateField(auto_now_add=True)
    CREATED_ON_TIME = models.TimeField(auto_now_add=True)

    UPDATED_ON_DATE = models.DateField(null=True, blank=True)
    UPDATED_ON_TIME = models.TimeField(null=True, blank=True)

    SMS_DATE = models.DateField(null=True, blank=True)
    SMS_TIME = models.TimeField(null=True, blank=True)

    EMAIL_DATE = models.DateField(null=True, blank=True)
    EMAIL_TIME = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = "device_status_alarm_log"
