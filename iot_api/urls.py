from django.urls import path, include
from rest_framework import routers
from django.urls import path, include
from rest_framework import routers
from . import views
from .views import current_user_api, user_org_centre_api


from .views import (
    DeviceReadingLogViewSet, MasterDeviceViewSet, CompassDatesViewSet,
    MasterOrganizationViewSet, MasterParameterViewSet, MasterSensorViewSet,
    SeUserViewSet, SensorParameterLinkViewSet, DeviceSensorLinkViewSet,
    DeviceAlarmCallLogViewSet, DeviceAlarmLogViewSet, MasterUOMViewSet , MasterCentreViewSet, MasterRoleViewSet ,CentreOrganizationLinkViewSet, MasterUserViewSet , UserOrganizationCentreLinkViewSet, MasterNotificationTimeViewSet , DeviceCategoryViewSet , MasterSubscriptionInfoViewSet, MasterPlanTypeViewSet, Subscription_HistoryViewSet,DeviceStatusAlarmLogViewSet)

# Router setup
router = routers.DefaultRouter()
router.register(r'devicereadinglog', DeviceReadingLogViewSet)
router.register(r'masterdevice', MasterDeviceViewSet)
router.register(r'compassdates', CompassDatesViewSet)
router.register(r'masterorganization', MasterOrganizationViewSet)
router.register(r'masterparameter', MasterParameterViewSet)
router.register(r'mastersensor', MasterSensorViewSet)
router.register(r'seuser', SeUserViewSet)
router.register(r'sensorparameterlink', SensorParameterLinkViewSet)
router.register(r'devicesensorlink', DeviceSensorLinkViewSet)
router.register(r'devicealarmcalllog', DeviceAlarmCallLogViewSet)
router.register(r'devicealarmlog', DeviceAlarmLogViewSet)
router.register(r'masteruom', MasterUOMViewSet)
router.register(r'mastercentre', MasterCentreViewSet)
router.register(r'masterrole', MasterRoleViewSet)
router.register(r'centreorganizationlink' , CentreOrganizationLinkViewSet)
router.register(r'masteruser', MasterUserViewSet)
router.register(r'userorganizationcentrelink', UserOrganizationCentreLinkViewSet )
router.register(r'masternotificationtime', MasterNotificationTimeViewSet)
router.register(r'devicecategory' , DeviceCategoryViewSet)
router.register(r'mastersubscriptioninfo', MasterSubscriptionInfoViewSet)
router.register(r'masterplantype', MasterPlanTypeViewSet)
router.register(r'subscriptionhistory', Subscription_HistoryViewSet)
router.register(r'devicestatusalarmlog', DeviceStatusAlarmLogViewSet)


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    # path('alert/', views.some_iot_alert_view, name='alert'),
    path('api/', include(router.urls)),
    path('user/', views.user_dashboard, name='user'),
    path("api/currentuser/", current_user_api, name="current_user"),
    path("api/userorgcentre/", user_org_centre_api, name="user_org_centre"),
    path('api/devicecheck/', views.devicecheck, name='devicecheck'),
    path('devicecheck/<int:device_id>/', views.devicecheck, name='devicecheck'),
    
]
