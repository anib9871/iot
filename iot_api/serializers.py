from rest_framework import serializers
from django import forms
from .models import DeviceAlarmLog
from django.contrib.auth.hashers import make_password
from .models import (
    DeviceReadingLog, MasterDevice, CompassDates,
    MasterOrganization, MasterParameter, MasterSensor,
    SeUser, SensorParameterLink, DeviceSensorLink,
    DeviceAlarmCallLog, DeviceAlarmLog, MasterUOM,MasterCentre, MasterRole , CentreOrganizationLink, MasterUser, UserOrganizationCentreLink,MasterNotificationTime,DeviceCategory, MasterSubscriptionInfo, Master_Plan_Type, SubscriptionHistory,DeviceStatusAlarmLog
)

# -------------------------
# CompassDates
# -------------------------
class CompassDatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompassDates
        fields = '__all__'

# -------------------------
# MasterDevice
# -------------------------
class MasterDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterDevice
        fields = ['DEVICE_ID','DEVICE_NAME','CATEGORY_ID','ORGANIZATION_ID','CENTRE_ID','DEVICE_STATUS']

# -------------------------
# DeviceReadingLog
# -------------------------
# # serializers.py
from rest_framework import serializers
from .models import DeviceReadingLog, MasterDevice

class DeviceReadingLogSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DeviceReadingLog
        fields = ['DEVICE_ID', 'SENSOR_ID', 'PARAMETER_ID', 'READING','READING_DATE','READING_TIME']

    def create(self, validated_data):
        device_id = validated_data.get('DEVICE_ID')

        try:
            master = MasterDevice.objects.get(DEVICE_ID=device_id)
        except MasterDevice.DoesNotExist:
            raise serializers.ValidationError({"DEVICE_ID": "Device not found in master_device"})

        # Add org and centre automatically
        validated_data['ORGANIZATION_ID'] = master.ORGANIZATION_ID
        validated_data['CENTRE_ID'] = master.CENTRE_ID

        return DeviceReadingLog.objects.create(**validated_data)


# -------------------------
# MasterOrganization
# -------------------------
class MasterOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterOrganization
        fields = ['ORGANIZATION_ID','ORGANIZATION_NAME']
        read_only_fields = ['id'] 

# -------------------------
# MasterParameter
# -------------------------
class MasterParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterParameter
        fields = ['PARAMETER_ID', 'PARAMETER_NAME', 'UPPER_THRESHOLD', 'LOWER_THRESHOLD', 'THRESHOLD', 'UOM_ID']

# -------------------------
# MasterSensor
# -------------------------
class MasterSensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterSensor
        fields = ['SENSOR_ID','SENSOR_NAME','SENSOR_TYPE','SENSOR_STATUS']

# -------------------------
# SeUser
# -------------------------
class SeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeUser
        fields = '__all__'

# -------------------------
# SensorParameterLink
# -------------------------
class SensorParameterLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorParameterLink
        fields = ['id', 'SENSOR_ID','PARAMETER_ID']
# -------------------------
# DeviceSensorLink
# -------------------------
class DeviceSensorLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceSensorLink
        fields = ['id','DEVICE_ID', 'SENSOR_ID','ORGANIZATION_ID','CENTRE_ID']
        

# -------------------------
# DeviceAlarmCallLog
# -------------------------
class DeviceAlarmCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceAlarmCallLog
        fields = '__all__'

# -------------------------
# DeviceAlarmLog
# -------------------------
class DeviceAlarmLogSerializer(serializers.ModelSerializer):
    ALARM_TIME = serializers.TimeField(format='%H:%M:%S')
    NORMALIZED_TIME = serializers.TimeField(format='%H:%M:%S', required=False, allow_null=True)

    class Meta:
        model = DeviceAlarmLog
        fields = ["id","ALARM_TIME","NORMALIZED_TIME","DEVICE_ID","SENSOR_ID","PARAMETER_ID","ALARM_DATE","READING","NORMALIZED_DATE","SMS_DATE","SMS_TIME","EMAIL_DATE",	"EMAIL_TIME","NORMALIZED_SMS_DATE",	"NORMALIZED_SMS_TIME","NORMALIZED_EMAIL_DATE","NORMALIZED_EMAIL_TIME","ORGANIZATION_ID","CENTRE_ID", "IS_ACTIVE"]


# UOM

class MasterUOMSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterUOM
        fields = ['UOM_ID', 'UOM_NAME'] 

# Center


class MasterCentreSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterCentre
        fields = ['CENTRE_ID','ORGANIZATION_ID', 'CENTRE_NAME']

#Role

class MasterRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterRole
        fields = ['ROLE_ID', 'ROLE_NAME']

# -------------------------
# CentreOrganizationLink
# -------------------------
class CentreOrganizationLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentreOrganizationLink
        fields = ['id','ORGANIZATION_ID','CENTRE_ID']


# -------------------------
# MasterUser
# -------------------------
import re
class MasterUserSerializer(serializers.ModelSerializer):
    SEND_SMS = serializers.BooleanField(required=False)
    SEND_EMAIL = serializers.BooleanField(required=False)

    class Meta:
        model = MasterUser
        fields = [
            'USER_ID',
            'ACTUAL_NAME',
            'USERNAME',
            'ROLE_ID',
            'PHONE',
            'SEND_SMS',
            'EMAIL',
            'SEND_EMAIL',
            'PASSWORD',
            'VALIDITY_START',
            'CREATED_BY',
            'VALIDITY_END'
        ]
        extra_kwargs = {
            "PASSWORD": {"write_only": False},  # Don't return password in API
        }

    def validate_PASSWORD(self, value):
        """Strong password validation"""
        # Minimum 8 chars, 1 upper, 1 lower, 1 digit, 1 special char
        regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$'
        if not re.match(regex, value):
            raise serializers.ValidationError(
                "Password must be min 8 chars, include 1 uppercase, 1 lowercase, 1 number, and 1 special character."
            )
        return make_password(value)  # Hash the password before saving
        
# -------------------------
# User Organization Centre Link
# -------------------------
class UserOrganizationCentreLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserOrganizationCentreLink
        fields = ['id','USER_ID','ORGANIZATION_ID','CENTRE_ID','created_by']


# -------------------------
# Master Notification Time
# -------------------------
class MasterNotificationTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterNotificationTime
        fields = ["id",'NOTIFICATION_TIME','ORGANIZATION_ID']

# -------------------------
# Device Category
# -------------------------
class DeviceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceCategory
        fields = ["CATEGORY_ID","CATEGORY_NAME"]


# -------------------------
# Master SubcriptionInfo
# -------------------------
class MasterSubscriptionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterSubscriptionInfo
        fields = ["Subscription_ID","Package_Name"]

# -------------------------
# Plan Type
# -------------------------
class Master_PlanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Master_Plan_Type
        fields = ["Plan_ID","Plan_Name"]

class Subscription_HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionHistory
        fields = ["id","Device_ID","Subscription_Start_date","Subcription_End_date"	,"Subscription_ID","Plan_ID","Payment_Date","Status"]


class DeviceStatusAlarmLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStatusAlarmLog
        fields = "__all__"
