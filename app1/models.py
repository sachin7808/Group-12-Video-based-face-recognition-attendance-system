from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import time
from django.db.models import Sum
from django.db.models.signals import post_save
from django.dispatch import receiver

   
# Department Model
class Department(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name

# Updated Student Model with Courses, Lessons, and Session
class Student(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=15)
    face_embedding = models.JSONField(blank=True, null=True)
    authorized = models.BooleanField(default=False)
    roll_no = models.CharField(max_length=20,unique=True)
    address = models.TextField()
    date_of_birth = models.DateField()
    joining_date = models.DateField()
    mother_name = models.CharField(max_length=255)
    father_name = models.CharField(max_length=255)
    department = models.ManyToManyField(Department, related_name="students")

    def __str__(self):
        return self.name



# Late Check-In Policy Model
class LateCheckInPolicy(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name="late_checkin_policy")

    def get_default_start_time():
        return time(8, 0)  # Default time as 8:00 AM

    start_time = models.TimeField(default=get_default_start_time)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.student.name} - Late Check-In After {self.start_time}"

# Signal to create default LateCheckInPolicy for each student
@receiver(post_save, sender=Student)
def create_late_checkin_policy(sender, instance, created, **kwargs):
    if created:
        LateCheckInPolicy.objects.create(student=instance)


# Attendance Model
class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent')], default='Absent')
    is_late = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.name} - {self.date}"

    def mark_checked_in(self):
        self.check_in_time = timezone.now()
        current_local_time = timezone.localtime(self.check_in_time)
        # Use CutOffPolicy if available
        cutoff_policy = getattr(self.student, 'cutoff_policy', None)
        if cutoff_policy:
          cutoff_time = current_local_time.replace(
            hour=cutoff_policy.cutoff_time.hour,
            minute=cutoff_policy.cutoff_time.minute,
            second=0,
            microsecond=0
            )
        else:
        # fallback to 9:00 AM if no policy
         cutoff_time = current_local_time.replace(hour=9, minute=0, second=0, microsecond=0)

       # Apply cutoff logic
        if current_local_time > cutoff_time:
         self.status = 'Absent'
        else:
         self.status = 'Present'

        # Fetch the student's late check-in policy
        policy = self.student.late_checkin_policy
        if policy:
            # Convert the late check-in time to the local timezone
            current_local_time = timezone.localtime()
            late_check_in_threshold = current_local_time.replace(
                hour=policy.start_time.hour,
                minute=policy.start_time.minute,
                second=0,
                microsecond=0
            )

            # Check if the check-in time is late
            if self.check_in_time > late_check_in_threshold:
                self.is_late = True

        

        self.save()

    def mark_checked_out(self):
        if self.check_in_time:
            self.check_out_time = timezone.now()
            self.save()
        else:
            raise ValueError("Cannot mark check-out without check-in.")

    def calculate_duration(self):
        if self.check_in_time and self.check_out_time:
            duration = self.check_out_time - self.check_in_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        return None

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            self.date = timezone.now().date()
        super().save(*args, **kwargs)

 #######################################################

######################################################################
class CameraConfiguration(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Give a name to this camera configuration")
    camera_source = models.CharField(max_length=255, help_text="Camera index (0 for default webcam or RTSP/HTTP URL for IP camera)")
    threshold = models.FloatField(default=0.6, help_text="Face recognition confidence threshold")
    location = models.CharField(max_length=255, null=True, default='Gate 1', help_text="Location of the camera (optional)")

    def __str__(self):
        return self.name



# Email Settings
class EmailConfig(models.Model):
    email_host = models.CharField(max_length=255)
    email_port = models.IntegerField()
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.CharField(max_length=255)
    email_host_password = models.CharField(max_length=255)

    def __str__(self):
        return f"Email Configuration for {self.email_host_user}"
    
###########################################################
from django.db import models

class Settings(models.Model):
    student = models.OneToOneField('Student', on_delete=models.CASCADE, related_name='settings', null=True, blank=True)  # Link to student
    check_out_time_threshold = models.IntegerField(default=60)  # Default 8 hours in seconds

    def __str__(self):
        return f"Settings (Student: {self.student.name if self.student else 'Global'}, Check-out Time Threshold: {self.check_out_time_threshold} seconds)"

# Signal to create default Settings for each student
@receiver(post_save, sender=Student)
def create_default_settings(sender, instance, created, **kwargs):
    if created:
        Settings.objects.create(student=instance)  # Automatically create the Settings object for the new student




class CutOffPolicy(models.Model):
    student = models.OneToOneField('Student', on_delete=models.CASCADE, related_name="cutoff_policy")

    def get_default_cutoff_time():
        return time(9, 0)  # Default is 9:00 AM

    cutoff_time = models.TimeField(default=get_default_cutoff_time)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.student.name} - Absent After {self.cutoff_time}"

@receiver(post_save, sender=Student)
def create_cutoff_policy(sender, instance, created, **kwargs):
    if created:
        CutOffPolicy.objects.create(student=instance)
