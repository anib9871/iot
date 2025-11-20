from django.contrib import admin
from .models import (
    CompassDates,
    DeviceAlarmCallLog,
    DeviceAlarmLog,
    DeviceReadingLog,
    DeviceSensorLink,
    MasterDevice,
    MasterOrganization,
    MasterParameter,
    MasterSensor,
    SeUser,
    SensorParameterLink, MasterRole , CentreOrganizationLink , MasterUser, UserOrganizationCentreLink,MasterNotificationTime,DeviceCategory , MasterSubscriptionInfo , Master_Plan_Type , SubscriptionHistory,DeviceStatusAlarmLog
)
from django import forms
# from .models import MasterUser
# Role

from . import models


# 1️⃣ Compass Dates
@admin.register(CompassDates)
class CompassDatesAdmin(admin.ModelAdmin):
    list_display = ('ORGANIZATION_ID', 'BRANCH_ID', 'CMPS_DT')
    search_fields = ('ORGANIZATION_ID', 'BRANCH_ID')
    list_filter = ('CMPS_DT',)

# 2️⃣ Device Alarm Call Log
@admin.register(DeviceAlarmCallLog)
class DeviceAlarmCallLogAdmin(admin.ModelAdmin):
    list_display = ('DEVICE_ID','SENSOR_ID','PARAMETER_ID','ALARM_DATE','ALARM_TIME','PHONE_NUM','CALL_DATE','CALL_TIME','SMS_CALL_FLAG')
    search_fields = ('DEVICE_ID','SENSOR_ID','PARAMETER_ID','PHONE_NUM')
    list_filter = ('ALARM_DATE',)

# 3️⃣ Device Alarm Log
@admin.register(DeviceAlarmLog)
class DeviceAlarmLogAdmin(admin.ModelAdmin):
    list_display = ('DEVICE_ID','SENSOR_ID','PARAMETER_ID','ALARM_DATE','ALARM_TIME','READING')
    search_fields = ('DEVICE_ID','SENSOR_ID','PARAMETER_ID')
    list_filter = ('ALARM_DATE',)

# 4️⃣ Device Reading Log
@admin.register(DeviceReadingLog)
class DeviceReadingLogAdmin(admin.ModelAdmin):
    list_display = ('DEVICE_ID','SENSOR_ID','PARAMETER_ID','READING_DATE','READING_TIME','READING')
    search_fields = ('DEVICE_ID','SENSOR_ID','PARAMETER_ID')
    list_filter = ('READING_DATE',)

# 5️⃣ Device Sensor Link
@admin.register(DeviceSensorLink)
class DeviceSensorLinkAdmin(admin.ModelAdmin):
    list_display = ('DEVICE_ID','SENSOR_ID','ORGANIZATION_ID','CENTRE_ID')
    search_fields = ('DEVICE_ID','SENSOR_ID')
    list_filter = ('ORGANIZATION_ID','CENTRE_ID')

# 6️⃣ Master Device
@admin.register(MasterDevice)
class MasterDeviceAdmin(admin.ModelAdmin):
    list_display = ('DEVICE_ID','DEVICE_NAME','DEVICE_MNEMONIC','DEVICE_STATUS','ORGANIZATION_ID','CENTRE_ID',)
    search_fields = ('DEVICE_NAME','DEVICE_MNEMONIC')
    list_filter = ('DEVICE_STATUS',)

# 7️⃣ Master Organization
@admin.register(MasterOrganization)
class MasterOrganizationAdmin(admin.ModelAdmin):
    list_display = ('ORGANIZATION_ID','ORGANIZATION_NAME','ORGANIZATION_STATUS')
    search_fields = ('ORGANIZATION_NAME',)
    list_filter = ('ORGANIZATION_STATUS',)

# 8️⃣ Master Parameter
@admin.register(MasterParameter)
class MasterParameterAdmin(admin.ModelAdmin):
    list_display = ('PARAMETER_ID','PARAMETER_NAME','UPPER_THRESHOLD','LOWER_THRESHOLD','THRESHOLD','PARAMETER_STATUS','ORGANIZATION_ID','CENTRE_ID')
    search_fields = ('PARAMETER_NAME',)
    list_filter = ('PARAMETER_STATUS',)

# 9️⃣ Master Sensor
@admin.register(MasterSensor)
class MasterSensorAdmin(admin.ModelAdmin):
    list_display = ('SENSOR_ID','SENSOR_NAME','SENSOR_TYPE','SENSOR_STATUS','ORGANIZATION_ID','CENTRE_ID')
    search_fields = ('SENSOR_NAME',)
    list_filter = ('SENSOR_STATUS',)

# 🔟 SE User
@admin.register(SeUser)
class SeUserAdmin(admin.ModelAdmin):
    list_display = ('USER_ID','USER_NAME','LOGIN_ID','DB_DRIVER','DB_URL')
    search_fields = ('USER_NAME','LOGIN_ID')
    list_filter = ()

# 1️⃣1️⃣ Sensor Parameter Link
@admin.register(SensorParameterLink)
class SensorParameterLinkAdmin(admin.ModelAdmin):
    list_display = ('SENSOR_ID','PARAMETER_ID','ORGANIZATION_ID','CENTRE_ID')
    search_fields = ('SENSOR_ID','PARAMETER_ID')
    list_filter = ('ORGANIZATION_ID','CENTRE_ID')


@admin.register(models.MasterRole)
class MasterRoleAdmin(admin.ModelAdmin):
    list_display = ('ROLE_ID', 'ROLE_NAME')

#  Centre Organization Link
@admin.register(CentreOrganizationLink)
class CentreOrganizationLinkAdmin(admin.ModelAdmin):
    list_display = ('ORGANIZATION_ID','CENTRE_ID')
    search_fields = ('ORGANIZATION_ID','CENTRE_ID')
    list_filter = ('ORGANIZATION_ID','CENTRE_ID')


class MasterUserForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirm Password"
    )

    class Meta:
        model = MasterUser
        fields = [
            "ACTUAL_NAME",
            "USERNAME",
            "PASSWORD",
            "EMAIL",
            "VALIDITY_START",
            "VALIDITY_END",
        ]
        widgets = {
            "PASSWORD": forms.PasswordInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("PASSWORD")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match")

        return cleaned_data


@admin.register(MasterUser)
class MasterUserAdmin(admin.ModelAdmin):
    form = MasterUserForm
    list_display = ("USER_ID", "ACTUAL_NAME", "USERNAME", "PHONE","SEND_SMS","EMAIL","SEND_EMAIL", "VALIDITY_START", "VALIDITY_END")
    search_fields = ("ACTUAL_NAME", "USERNAME","PHONE", "EMAIL")
    list_filter = ("VALIDITY_START", "VALIDITY_END")

# User Organization Centre Link
@admin.register(models.UserOrganizationCentreLink)
class UserOrganizationCentreLinkAdmin(admin.ModelAdmin):
    list_display = ("ORGANIZATION_ID","CENTRE_ID","USER_ID")
    search_fields = ("ORGANIZATION_ID","CENTRE_ID","USER_ID")
    list_filter = ("ORGANIZATION_ID","CENTRE_ID","USER_ID")

# Master Notification Time
@admin.register(models.MasterNotificationTime)
class MasterNotificationTimeAdmin(admin.ModelAdmin):
    list_display = ("NOTIFICATION_TIME","ORGANIZATION_ID")
    search_fields = ("NOTIFICATION_TIME","ORGANIZATION_ID")
    list_filter = ("NOTIFICATION_TIME","ORGANIZATION_ID")

# Device Category
@admin.register(models.DeviceCategory)
class DeviceCategoryAdmin(admin.ModelAdmin):
    list_display =("CATEGORY_ID","CATEGORY_NAME")
    search_fields =("CATEGORY_ID","CATEGORY_NAME")
    list_filter =("CATEGORY_ID","CATEGORY_NAME")

# Master_SubscriptionInfo
@admin.register(models.MasterSubscriptionInfo)
class MasterSubscriptionInfoAdmin(admin.ModelAdmin):
    list_display = ("Subscription_ID", "Package_Name", "CRT_date", "CRT_BY")
    search_fields = ("Subscription_ID", "Package_Name", "CRT_date", "CRT_BY")
    list_filter = ("Subscription_ID", "Package_Name", "CRT_date", "CRT_BY")


# Plan_Type
@admin.register(models.Master_Plan_Type)
class MasterPlanTypeAdmin(admin.ModelAdmin):
    list_display = ("Plan_ID", "Plan_Name")
    search_fields = ("Plan_ID", "Plan_Name")
    list_filter = ("Plan_ID", "Plan_Name")

# subscription History
@admin.register(models.SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ("id","Device_ID","Subscription_Start_date"	,"Subcription_End_date"	,"Subscription_ID","Plan_ID","Payment_Date")
    search_fields = ("id","Device_ID","Subscription_Start_date"	,"Subcription_End_date"	,"Subscription_ID","Plan_ID","Payment_Date")
    list_filter = ("id","Device_ID","Subscription_Start_date"	,"Subcription_End_date"	,"Subscription_ID","Plan_ID","Payment_Date")

@admin.register(DeviceStatusAlarmLog)
class DeviceStatusAlarmLogAdmin(admin.ModelAdmin):
    list_display = (
        "DEVICE_STATUS_ALARM_ID",
        "DEVICE_ID",
        "DEVICE_STATUS",
        "IS_ACTIVE",
        "CREATED_ON_DATE",
        "CREATED_ON_TIME",
        "UPDATED_ON_DATE",
        "UPDATED_ON_TIME",
    )
    list_filter = ("IS_ACTIVE", "DEVICE_STATUS")
    search_fields = ("DEVICE_ID",)
