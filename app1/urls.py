from django.urls import path
from . import views

urlpatterns = [

    path('', views.admin_dashboard, name='admin_dashboard'),
   
    # Student Registration and Attendance
    path('register_student/', views.register_student, name='register_student'),
    path('mark_attendance', views.mark_attendance, name='mark_attendance'),
    path('register_success/', views.register_success, name='register_success'),
    path('students/', views.student_list, name='student-list'),
    path('students/<int:pk>/', views.student_detail, name='student-detail'),
    path('students/attendance/', views.student_attendance_list, name='student_attendance_list'),
    path('students/<int:pk>/authorize/', views.student_authorize, name='student-authorize'),
    path('students/<int:pk>/delete/', views.student_delete, name='student-delete'),
    path('student/edit/<int:pk>/', views.student_edit, name='student-edit'),
   
    
    # Capture and Recognize Views
    path('capture-and-recognize/', views.capture_and_recognize, name='capture_and_recognize'),
    path('recognize_with_cam/', views.capture_and_recognize_with_cam, name='capture_and_recognize_with_cam'),
    
    # User Authentication Views
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Attendance Notifications
    path('send_attendance_notifications', views.send_attendance_notifications, name='send_attendance_notifications'),
    
    # Late cutoff Policies
    path('cutoff/', views.cutoff_policy_list, name='cutoff_policy_list'),
    path('cutoff/create/', views.create_cutoff_policy, name='create_cutoff_policy'),
    path('cutoff/update/<int:policy_id>/', views.update_cutoff_policy, name='update_cutoff_policy'),
    path('cutoff/delete/<int:policy_id>/', views.delete_cutoff_policy, name='delete_cutoff_policy'),
   
    
    # Late Check-in Policies
    path('late_checkin_policy_list/', views.late_checkin_policy_list, name='late_checkin_policy_list'),
    path('late-checkin-policies/create/', views.create_late_checkin_policy, name='create_late_checkin_policy'),
    path('late-checkin-policies/<int:policy_id>/update/',views.update_late_checkin_policy, name='update_late_checkin_policy'),
    path('delete-late-checkin-policy/<int:policy_id>/', views.delete_late_checkin_policy, name='delete_late_checkin_policy'),
    
    ########################################################### Camera Configurations
    path('camera-config/', views.camera_config_create, name='camera_config_create'),
    path('camera-config/list/', views.camera_config_list, name='camera_config_list'),
    path('camera-config/update/<int:pk>/', views.camera_config_update, name='camera_config_update'),
    path('camera-config/delete/<int:pk>/', views.camera_config_delete, name='camera_config_delete'),
    
    
    # For email adding and upateing and editing
    path('email-configs/', views.view_email_configs, name='view_email_configs'),
    path('email-configs/add/', views.add_email_config, name='add_email_config'),
    path('email-configs/edit/<int:email_config_id>/', views.edit_email_config, name='edit_email_config'),
    path('email-configs/delete/<int:email_config_id>/', views.delete_email_config, name='delete_email_config'),

    
    # Department URLs
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/update/<int:pk>/', views.department_update, name='department_update'),
    path('departments/delete/<int:pk>/', views.department_delete, name='department_delete'),

    # This url is for check out time policy settings
    path('settings-list/', views.settings_list, name='settings_list'),
    path('settings/create/', views.create_settings, name='create_settings'),
    path('settings/<int:pk>/update/', views.update_settings, name='update_settings'),
    path('settings/<int:pk>/delete/', views.delete_settings, name='delete_settings'),

]
