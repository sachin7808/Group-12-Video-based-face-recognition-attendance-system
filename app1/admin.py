from django.contrib import admin
from .models import (
    Department, Student, 
    LateCheckInPolicy, Attendance, 
    CameraConfiguration, EmailConfig, Settings, CutOffPolicy
)


admin.site.site_header = "Hello Admin"
admin.site.site_title = "My Admin Panel"
admin.site.index_title = "Welcome to Attendance System"

# ==================== Department Admin ====================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

# ==================== Student Admin ====================
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'roll_no', 'email', 'phone_number', 'authorized')
    search_fields = ('name', 'roll_no', 'email')
    list_filter = ('authorized',)  # ✅ Fixed: Made it a tuple
    ordering = ('name',)

# ==================== LateCheckInPolicy Admin ====================
@admin.register(LateCheckInPolicy)
class LateCheckInPolicyAdmin(admin.ModelAdmin):
    list_display = ('student', 'start_time', 'description')
    search_fields = ('student__name',)

# ==================== cutoffPolicy Admin ====================
@admin.register(CutOffPolicy)
class CutOffPolicyAdmin(admin.ModelAdmin):
    list_display = ('student', 'cutoff_time', 'description')
    search_fields = ('student__name', 'student__roll_no')

# ==================== Attendance Admin ====================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'check_in_time', 'check_out_time', 'status', 'is_late')
    search_fields = ('student__name', 'date')
    list_filter = ('status', 'is_late')

# ==================== CameraConfiguration Admin ====================
@admin.register(CameraConfiguration)
class CameraConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'camera_source', 'threshold')
    search_fields = ('name', 'camera_source')

# ==================== EmailConfig Admin ====================
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ('email_host', 'email_port', 'email_use_tls', 'email_host_user')
    search_fields = ('email_host', 'email_host_user')

admin.site.register(EmailConfig, EmailConfigAdmin)

# ==================== Settings Admin ====================
@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'student_name', 'check_out_time_threshold', 'is_global_setting')
    list_filter = ('student',)
    search_fields = ('student__name',)
    ordering = ('-id',)

    def student_name(self, obj):
        return obj.student.name if obj.student else 'Global'
    student_name.short_description = 'Student Name'

    def is_global_setting(self, obj):
        return obj.student is None
    is_global_setting.short_description = 'Global Setting'
    is_global_setting.boolean = True
