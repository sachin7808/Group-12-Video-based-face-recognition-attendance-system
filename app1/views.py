import os
import cv2 # type: ignore
import numpy as np # type: ignore
import torch # type: ignore
from insightface.app import FaceAnalysis # type: ignore
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from .models import Student, Attendance
from django.core.files.base import ContentFile
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
import time
from django.utils.timezone import now
import base64
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Student, Attendance,CameraConfiguration,EmailConfig,Settings
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now as timezone_now
from datetime import datetime, timedelta
from django.utils.timezone import localtime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Student, Attendance
from django.db.models import Count
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.shortcuts import render, redirect
from django.core.files.base import ContentFile
from django.contrib.auth.models import Group
import pygame  # Import pygame for playing sounds
import threading
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse
from django.contrib import messages
from .models import LateCheckInPolicy
from .forms import LateCheckInPolicyForm
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Sum
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import render
from django.core.mail import send_mail
from django.template.loader import render_to_string
from .forms import StudentEditForm
from django.core.mail import send_mail
from django.shortcuts import render
from django.contrib import messages
from django.template.loader import render_to_string
from .models import Attendance, EmailConfig  # Import models
from django.shortcuts import render, get_object_or_404, redirect
from .models import  Department
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import EmailConfig
from django.shortcuts import render, get_object_or_404
from .models import CutOffPolicy
from .forms import CutOffPolicyForm
###############################################################


##############################################################
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    
    # Count total students
    total_students = Student.objects.count()

    # Total attendance records for today
    total_attendance = Attendance.objects.count()

    # Total present students for today
    total_present = Attendance.objects.filter(status='Present').count()

    # Total absent students for today
    total_absent = Attendance.objects.filter(status='Absent').count()

    # Total late check-ins for today
    total_late_checkins = Attendance.objects.filter(is_late=True).count()

    # Total check-ins for today
    total_checkins = Attendance.objects.filter(check_in_time__isnull=False).count()

    # Total check-outs for today
    total_checkouts = Attendance.objects.filter(check_out_time__isnull=False).count()

    # Total number of cameras
    total_cameras = CameraConfiguration.objects.count()
   
    # Passing the data to the template
    context = {
        'total_students': total_students,
        'total_attendance': total_attendance,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_late_checkins': total_late_checkins,
        'total_checkins': total_checkins,
        'total_checkouts': total_checkouts,
        'total_cameras': total_cameras,

    }

    return render(request, 'admin/admin-dashboard.html', context)

##############################################################

def mark_attendance(request):
    return render(request, 'Mark_attendance.html')

#############################################################
# Initialize Ratinaface and Arcface
face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))

# Function to detect and encode faces
def detect_and_encode(image):
    """
    Detects faces in the input image and returns 512-dimensional ArcFace embeddings.
    """
    faces = face_app.get(image)
    encodings = []

    for face in faces:
        if face.embedding is not None:
            encodings.append(face.embedding)

    return encodings

# Function to encode uploaded images
def encode_uploaded_images():
    known_face_encodings = []
    known_face_names = []

    # Fetch all students — temporarily remove authorized filter for debugging
    uploaded_images = Student.objects.all()  # change to .filter(authorized=True) later if needed

    for student in uploaded_images:
        if student.face_embedding:
            embedding = np.array(student.face_embedding, dtype=np.float32)
            embedding = embedding / np.linalg.norm(embedding)  # normalize the embedding
            known_face_encodings.append(embedding)
            known_face_names.append(student.name)

    return known_face_encodings, known_face_names



# Function to recognize faces
def recognize_faces(known_encodings, known_names, test_encodings, threshold=0.5):
    recognized_names = []

    for test_encoding in test_encodings:
        test_encoding = test_encoding / np.linalg.norm(test_encoding)  # Normalize
        similarities = np.dot(known_encodings, test_encoding) / (
            np.linalg.norm(known_encodings, axis=1) * np.linalg.norm(test_encoding)
        )
        best_match_idx = np.argmax(similarities)

        if similarities[best_match_idx] >= threshold:
            recognized_names.append(known_names[best_match_idx])
        else:
            recognized_names.append("Not Recognized")

    return recognized_names


############################################################################

@csrf_exempt
def capture_and_recognize(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Invalid request method.'}, status=405)

    try:
        current_time = timezone.now()
        today = current_time.date()

        settings = Settings.objects.first()
        if not settings:
            return JsonResponse({'message': 'Settings not configured.'}, status=500)

        global_check_out_threshold_seconds = settings.check_out_time_threshold

        # Mark absent students
        students = Student.objects.all()
        attendance_records = Attendance.objects.filter(date=today)
        absent_students = {student.id for student in students} - {record.student_id for record in attendance_records}
        Attendance.objects.bulk_create([
            Attendance(student_id=student_id, date=today, status='Absent')
            for student_id in absent_students
        ])
        attendance_records.filter(check_in_time__isnull=True, date=today).update(status='Absent')

        # Parse image data
        data = json.loads(request.body)
        image_data = data.get('image')
        if not image_data:
            return JsonResponse({'message': 'No image data received.'}, status=400)

        image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        np_img = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect and encode faces using InsightFace
        faces = face_app.get(frame_rgb)
        if not faces:
            return JsonResponse({'message': 'No face detected.'}, status=200)

        test_face_encodings = []
        for face in faces:
              aligned_face = face_app.align_crop(frame_rgb, face)
              embedding = face_app.model.get(aligned_face)
              embedding = embedding / np.linalg.norm(embedding)
              test_face_encodings.append(embedding)

        if not test_face_encodings:
            return JsonResponse({'message': 'Face embedding failed.'}, status=500)

        known_face_encodings, known_face_names = encode_uploaded_images()
        if not known_face_encodings:
            return JsonResponse({'message': 'No known faces available.'}, status=200)

        recognized_names = recognize_faces(
            np.array(known_face_encodings),
            known_face_names,
            test_face_encodings,
            threshold=0.5
        )

        attendance_response = []
        for name in recognized_names:
            if name == 'Not Recognized':
                attendance_response.append({
                    'name': 'Unknown',
                    'status': 'Face not recognized',
                    'check_in_time': None,
                    'check_out_time': None,
                    'image_url': '/static/notrecognize.png',
                    'play_sound': False
                })
                continue

            student = Student.objects.filter(name=name).first()
            if not student:
                continue

            student_threshold_seconds = (
                student.settings.check_out_time_threshold
                if student.settings and student.settings.check_out_time_threshold is not None
                else global_check_out_threshold_seconds
            )

            attendance, created = Attendance.objects.get_or_create(student=student, date=today)

            if created or not attendance.check_in_time:
                attendance.mark_checked_in()
                attendance.save()
                attendance_response.append({
                    'name': name,
                    'status': 'Checked-in',
                    'check_in_time': attendance.check_in_time.isoformat(),
                    'check_out_time': None,
                    'image_url': '/static/success.png',
                    'play_sound': True
                })
            elif not attendance.check_out_time and current_time >= attendance.check_in_time + timedelta(seconds=student_threshold_seconds):
                attendance.mark_checked_out()
                attendance_response.append({
                    'name': name,
                    'status': 'Checked-out',
                    'check_in_time': attendance.check_in_time.isoformat(),
                    'check_out_time': attendance.check_out_time.isoformat(),
                    'image_url': '/static/success.png',
                    'play_sound': True
                })
            else:
                attendance_response.append({
                    'name': name,
                    'status': 'Already checked-in' if not attendance.check_out_time else 'Already checked-out',
                    'check_in_time': attendance.check_in_time.isoformat(),
                    'check_out_time': attendance.check_out_time.isoformat() if attendance.check_out_time else None,
                    'image_url': '/static/success.png',
                    'play_sound': False
                })

        return JsonResponse({'attendance': attendance_response}, status=200)
    except Exception as e:
        return JsonResponse({'message': f"Error: {str(e)}"}, status=500)
#######################################################################

# Function to detect and encode faces

def detect_and_encode_uploaded_image_for_register(image):
    faces = face_app.get(image)

    if faces:  # If there are any faces detected
        for face in faces:
            if face.embedding is not None:
                return face.embedding  # Already 512-dimensional vector

    return None


############################################################################################
# View to register a student
def register_student(request):
    if request.method == 'POST':
        try:
            # Get student information from the form
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            image_file = request.FILES.get('image')  # Uploaded image
            roll_no = request.POST.get('roll_no')
            address = request.POST.get('address')
            date_of_birth = request.POST.get('date_of_birth')
            joining_date = request.POST.get('joining_date')
            mother_name = request.POST.get('mother_name')
            father_name = request.POST.get('father_name')
            department_ids = request.POST.getlist('department')
            username = request.POST.get('username')
            password = request.POST.get('password')

            

            # Check for existing roll number
            if Student.objects.filter(roll_no=roll_no).exists():
                messages.error(request, 'Roll number already exists. Please use a different roll number.')
                return render(request, 'register_student.html')

            # Process the uploaded image to extract face embedding
            image_array = np.frombuffer(image_file.read(), np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            face_embedding = detect_and_encode_uploaded_image_for_register(image_rgb)

            if face_embedding is None:
                messages.error(request, 'No face detected in the uploaded image. Please upload a clear face image.')
                return render(request, 'register_student.html')

        
            # Create the student record
            student = Student(
               
                name=name,
                email=email,
                phone_number=phone_number,
                face_embedding=face_embedding.tolist(),  # Save the face embedding
                authorized=False,
                roll_no=roll_no,
                address=address,
                date_of_birth=date_of_birth,
                joining_date=joining_date,
                mother_name=mother_name,
                father_name=father_name,
            )
            student.save()
            student.department.set(Department.objects.filter(id__in=department_ids))
            messages.success(request, 'Registration successful! Welcome.')
            return redirect('register_success')

        except Exception as e:
            print(f"Error during registration: {e}")
            messages.error(request, 'An error occurred during registration. Please try again.')
            return render(request, 'register_student.html')

    departments = Department.objects.all()
  

    return render(request, 'register_student.html', {
        
        'departments': departments,
    })


########################################################################

# Success view after capturing student information and image
def register_success(request):
    return render(request, 'register_success.html')

#########################################################################
import csv
from django.http import HttpResponse #this is for showing Attendance list
def is_admin(user):
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def student_attendance_list(request):
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('attendance_date', '')
    roll_no_filter = request.GET.get('roll_no', '')
    status_filter = request.GET.get('status', '')
    export_csv = request.GET.get('export') == 'csv'

    students = Student.objects.all()

    if search_query:
        students = students.filter(name__icontains=search_query)

    if roll_no_filter:
        students = students.filter(roll_no__icontains=roll_no_filter)

    student_attendance_data = []
    total_attendance_count = 0
    export_data = []  # Store rows for CSV export

    for student in students:
        attendance_records = Attendance.objects.filter(student=student)

        if date_filter:
            attendance_records = attendance_records.filter(date=date_filter)

        processed_records = []
        for record in attendance_records:
            dynamic_status = record.status

            if status_filter and dynamic_status != status_filter:
                continue

            record.dynamic_status = dynamic_status
            processed_records.append(record)

            if export_csv:
                export_data.append([
                    student.name,
                    student.roll_no,
                    record.date,
                    record.check_in_time.strftime('%Y-%m-%d %H:%M:%S') if record.check_in_time else '',
                    record.check_out_time.strftime('%Y-%m-%d %H:%M:%S') if record.check_out_time else '',
                    dynamic_status,
                    "Yes" if record.is_late else "No",
                ])

        student_attendance_count = len(processed_records)
        total_attendance_count += student_attendance_count

        student_attendance_data.append({
            'student': student,
            'attendance_records': processed_records,
            'attendance_count': student_attendance_count
        })

    # If CSV export is requested
    if export_csv:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'

        writer = csv.writer(response)
        writer.writerow(['Name', 'Roll No', 'Date', 'Check-in Time', 'Check-out Time', 'Status', 'Late?'])
        for row in export_data:
            writer.writerow(row)
        return response

    context = {
        'student_attendance_data': student_attendance_data,
        'search_query': search_query,
        'date_filter': date_filter,
        'roll_no_filter': roll_no_filter,
        'status_filter': status_filter,
        'total_attendance_count': total_attendance_count
    }

    return render(request, 'student_attendance_list.html', context)




######################################################################

@staff_member_required
def student_list(request):
    students = Student.objects.all()
    return render(request, 'student_list.html', {'students': students})

@staff_member_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    return render(request, 'student_detail.html', {'student': student})

@staff_member_required
def student_authorize(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        authorized = request.POST.get('authorized', False)
        student.authorized = bool(authorized)
        student.save()
        return redirect('student-list')
    
    return render(request, 'student_authorize.html', {'student': student})

###############################################################################

def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        student.name = request.POST.get('name')
        student.email = request.POST.get('email')
        student.phone_number = request.POST.get('phone_number')
        student.roll_no = request.POST.get('roll_no')
        student.address = request.POST.get('address')
        student.date_of_birth = request.POST.get('date_of_birth')
        student.joining_date = request.POST.get('joining_date')
        student.mother_name = request.POST.get('mother_name')
        student.father_name = request.POST.get('father_name')
        student.authorized = 'authorized' in request.POST

        # Handle department as multiple select
        department_ids = request.POST.getlist('department')
        student.department.set(department_ids)

        student.save()

        messages.success(request, 'Student details updated successfully.')
        return redirect('student-detail', pk=student.pk)

    departments = Department.objects.all()
    return render(request, 'student_edit.html', {
        'student': student,
        'departments': departments
    })

###########################################################
# This views is for Deleting student
@staff_member_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'Student deleted successfully.')
        return redirect('student-list')  # Redirect to the student list after deletion
    
    return render(request, 'student_delete_confirm.html', {'student': student})

########################################################################

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

              
            return redirect('admin_dashboard')

        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'login.html')

#########################################################################

# This is for user logout
def user_logout(request):
    logout(request)
    return redirect('login')  # Replace 'login' with your desired redirect URL after logout
##############################################################################

#######################################################################################    

@staff_member_required
def send_attendance_notifications(request):
    # Fetch email configuration from the database
    email_config = EmailConfig.objects.first()  # Get the first email configuration or handle multiple configurations

    if email_config is None:
        messages.error(request, "No email configuration found!")
        return render(request, 'notification_sent.html')

    # Set up the email backend dynamically based on the configuration
    settings.EMAIL_HOST = email_config.email_host
    settings.EMAIL_PORT = email_config.email_port
    settings.EMAIL_USE_TLS = email_config.email_use_tls
    settings.EMAIL_HOST_USER = email_config.email_host_user
    settings.EMAIL_HOST_PASSWORD = email_config.email_host_password

    # Filter late students who haven't been notified
    late_attendance_records = Attendance.objects.filter(is_late=True , status='Present', email_sent=False)
    # Filter absent students who haven't been notified
    absent_students = Attendance.objects.filter(is_late=True,status='Absent', email_sent=False)

    # Process late students
    for record in late_attendance_records:
        student = record.student
        subject = f"Late Check-in Notification for {student.name}"

        # Render the email content from the HTML template for late students
        html_message = render_to_string(
            'email_templates/late_attendance_email.html',  # Path to the template
            {'student': student, 'record': record}  # Context to be passed into the template
        )

        recipient_email = student.email

        # Send the email with HTML content
        send_mail(
            subject,
            "This is an HTML email. Please enable HTML content to view it.",
            settings.EMAIL_HOST_USER,
            [recipient_email],
            fail_silently=False,
            html_message=html_message
        )

        # Mark email as sent to avoid resending
        record.email_sent = True
        record.save()

    # Process absent students
    for record in absent_students:
        student = record.student
        subject = "Absent Attendance Notification"

        # Render the email content from the HTML template for absent students
        html_message = render_to_string(
            'email_templates/absent_attendance_email.html',  # Path to the new template
            {'student': student, 'record': record}  # Context to be passed into the template
        )

        # Send the email notification for absent students
        send_mail(
            subject,
            "This is an HTML email. Please enable HTML content to view it.",
            settings.EMAIL_HOST_USER,
            [student.email],
            fail_silently=False,
            html_message=html_message
        )

        # After sending the email, update the `email_sent` field to True
        record.email_sent = True
        record.save()

    # Combine late and absent students for the response
    all_notified_students = late_attendance_records | absent_students

    # Fetch students who already received the email (email_sent=True)
    already_notified_students = Attendance.objects.filter(email_sent=True)

    # Display success message
    messages.success(request, "Attendance notifications have been sent successfully!")

    # Return a response with a template that displays the notified students
    return render(request, 'notification_sent.html', {
        'notified_students': already_notified_students  # Show only those who have been notified
    })


############################################################################################


##################################################################################
# views.py

@staff_member_required
def late_checkin_policy_list(request):
    policies = LateCheckInPolicy.objects.select_related('student').all()
    return render(request, 'latecheckinpolicy_list.html', {'policies': policies})

def create_late_checkin_policy(request):
    if request.method == 'POST':
        form = LateCheckInPolicyForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            if LateCheckInPolicy.objects.filter(student=student).exists():
                messages.error(request, f"A late check-in policy for {student} already exists.")
            else:
                form.save()
                messages.success(request, "Late check-in policy created successfully!")
                return redirect('late_checkin_policy_list')
    else:
        form = LateCheckInPolicyForm()

    return render(request, 'latecheckinpolicy_form.html', {'form': form})

@staff_member_required
def update_late_checkin_policy(request, policy_id):
    policy = get_object_or_404(LateCheckInPolicy, id=policy_id)
    if request.method == 'POST':
        form = LateCheckInPolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, "Late check-in policy updated successfully!")
            return redirect('late_checkin_policy_list')
    else:
        form = LateCheckInPolicyForm(instance=policy)

    return render(request, 'latecheckinpolicy_form.html', {'form': form, 'policy': policy})

@staff_member_required
def delete_late_checkin_policy(request, policy_id):
    policy = get_object_or_404(LateCheckInPolicy, id=policy_id)
    if request.method == 'POST':
        policy.delete()
        messages.success(request, "Late check-in policy deleted successfully!")
        return redirect('late_checkin_policy_list')
    return render(request, 'latecheckinpolicy_confirm_delete.html', {'policy': policy})

@staff_member_required
def cutoff_policy_list(request):
    policies = CutOffPolicy.objects.select_related('student').all()
    return render(request, 'cutoffpolicy_list.html', {'policies': policies})

@staff_member_required
def create_cutoff_policy(request):
    if request.method == 'POST':
        form = CutOffPolicyForm(request.POST)
        
        if form.is_valid():
            # If form is valid, save it
            student = form.cleaned_data['student']
            if CutOffPolicy.objects.filter(student=student).exists():
                messages.error(request, f"A cutoff policy for {student} already exists.")
            else:
                form.save()
                messages.success(request, "Cutoff policy created successfully!")
                return redirect('cutoff_policy_list')
    else:
        form = CutOffPolicyForm()

    return render(request, 'cutoffpolicy_form.html', {'form': form})


@staff_member_required
def update_cutoff_policy(request, policy_id):
    # Get the policy by id
    policy = get_object_or_404(CutOffPolicy, id=policy_id)

    # If the form is submitted with POST request
    if request.method == 'POST':
        form = CutOffPolicyForm(request.POST, instance=policy)
        
        # Check if form is valid
        if form.is_valid():
            form.save()  # Save the updated policy
            messages.success(request, "Cutoff policy updated successfully!")
            return redirect('cutoff_policy_list')  # Redirect after successful save
    else:
        form = CutOffPolicyForm(instance=policy)  # For GET request, show the existing data in form

    # Render the form page
    return render(request, 'cutoffpolicy_form.html', {'form': form, 'policy': policy})


@staff_member_required
def delete_cutoff_policy(request, policy_id):
    policy = get_object_or_404(CutOffPolicy, id=policy_id)
    if request.method == 'POST':
        policy.delete()
        messages.success(request, "Cutoff policy deleted successfully!")
        return redirect('cutoff_policy_list')
    return render(request, 'cutoffpolicy_confirm_delete.html', {'policy': policy})

#########################################################################################

def capture_and_recognize_with_cam(request):
    stop_events = []  # List to store stop events for each thread
    camera_threads = []  # List to store threads for each camera
    camera_windows = []  # List to store window names
    error_messages = []  # List to capture errors from threads

    def process_frame(cam_config, stop_event):
        """Thread function to capture and process frames for each camera."""
        cap = None
        window_created = False  # Flag to track if the window was created
        try:
            # Check if the camera source is a number (local webcam) or a string (IP camera URL)
            if cam_config.camera_source.isdigit():
                cap = cv2.VideoCapture(int(cam_config.camera_source))  # Use integer index for webcam
            else:
                cap = cv2.VideoCapture(cam_config.camera_source)  # Use string for IP camera URL

            if not cap.isOpened():
                raise Exception(f"Unable to access camera {cam_config.name}.")

            threshold = cam_config.threshold

            # Initialize pygame mixer for sound playback
            pygame.mixer.init()
            success_sound = pygame.mixer.Sound('static/success.wav')  # Load sound path

            window_name = f'Camera Location - {cam_config.location}'
            camera_windows.append(window_name)  # Track the window name

            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print(f"Failed to capture frame for camera: {cam_config.name}")
                    break  # If frame capture fails, break from the loop

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces using RetinaFace (via FaceAnalysis)
                faces = face_app.get(frame_rgb)
                if faces:
                    for face in faces:
                        bbox = face.bbox
                        face_embedding = face.embedding

                        # Compare the detected face embedding with known face encodings
                        known_face_encodings, known_face_names = encode_uploaded_images()  # Load known face encodings once
                        if known_face_encodings:
                            names = recognize_faces(
                                np.array(known_face_encodings), known_face_names, [face_embedding], threshold
                            )

                            for name in names:
                                # Draw bounding box and name on the frame
                                (x1, y1, x2, y2) = map(int, bbox)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                cv2.putText(frame, name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

                                if name != 'Not Recognized':
                                    students = Student.objects.filter(name=name)
                                    if students.exists():
                                        student = students.first()
                                        print(f"Recognized student: {student.name}")  # Debugging log

                                        # Fetch the check-out time threshold
                                        if student.settings:
                                            check_out_threshold_seconds = student.settings.check_out_time_threshold

                                        # Check if attendance exists for today
                                        attendance, created = Attendance.objects.get_or_create(
                                            student=student, date=now().date()
                                        )

                                        if attendance.check_in_time is None:
                                            attendance.mark_checked_in()
                                            success_sound.play()
                                            cv2.putText(
                                                frame, f"{name}, checked in.", (50, 50),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA
                                            )
                                            print(f"Attendance checked in for {student.name}")
                                        elif attendance.check_out_time is None:
                                            if now() >= attendance.check_in_time + timedelta(seconds=check_out_threshold_seconds):
                                                attendance.mark_checked_out()
                                                success_sound.play()
                                                cv2.putText(
                                                    frame, f"{name}, checked out.", (50, 50),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA
                                                )
                                                print(f"Attendance checked out for {student.name}")
                                            else:
                                                cv2.putText(
                                                    frame, f"{name}, already checked in.", (50, 50),
                                                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA
                                                )
                                        else:
                                            cv2.putText(
                                                frame, f"{name}, already checked out.", (50, 50),
                                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA
                                            )
                                            print(f"Attendance already completed for {student.name}")

                # Display frame in a separate window for each camera
                if not window_created:
                    cv2.namedWindow(window_name)  # Only create window once
                    window_created = True  # Mark window as created
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    stop_event.set()  # Signal the thread to stop when 'q' is pressed
                    break

        except Exception as e:
            print(f"Error in thread for {cam_config.name}: {e}")
            error_messages.append(str(e))  # Capture error message
        finally:
            if cap is not None:
                cap.release()
            if window_created:
                cv2.destroyWindow(window_name)  # Only destroy if window was created

    try:
        # Get all camera configurations
        cam_configs = CameraConfiguration.objects.all()
        if not cam_configs.exists():
            raise Exception("No camera configurations found. Please configure them in the admin panel.")

        # Create threads for each camera configuration
        for cam_config in cam_configs:
            stop_event = threading.Event()
            stop_events.append(stop_event)

            camera_thread = threading.Thread(target=process_frame, args=(cam_config, stop_event))
            camera_threads.append(camera_thread)
            camera_thread.start()

        # Keep the main thread running while cameras are being processed
        while any(thread.is_alive() for thread in camera_threads):
            time.sleep(1)  # Non-blocking wait, allowing for UI responsiveness

    except Exception as e:
        error_messages.append(str(e))  # Capture the error message
    finally:
        # Ensure all threads are signaled to stop
        for stop_event in stop_events:
            stop_event.set()

        # Ensure all windows are closed in the main thread
        for window in camera_windows:
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) >= 1:  # Check if window exists
                cv2.destroyWindow(window)

    # Check if there are any error messages
    if error_messages:
        # Join all error messages into a single string
        full_error_message = "\n".join(error_messages)
        return render(request, 'error.html', {'error_message': full_error_message})  # Render the error page with message

    return redirect('student_attendance_list')


##############################################################################

# Function to handle the creation of a new camera configuration
@login_required
@user_passes_test(is_admin)
def camera_config_create(request):
    # Check if the request method is POST, indicating form submission
    if request.method == "POST":
        # Retrieve form data from the request
        name = request.POST.get('name')
        camera_source = request.POST.get('camera_source')
        threshold = request.POST.get('threshold')

        try:
            # Save the data to the database using the CameraConfiguration model
            CameraConfiguration.objects.create(
                name=name,
                camera_source=camera_source,
                threshold=threshold,
            )
            # Redirect to the list of camera configurations after successful creation
            return redirect('camera_config_list')

        except IntegrityError:
            # Handle the case where a configuration with the same name already exists
            messages.error(request, "A configuration with this name already exists.")
            # Render the form again to allow user to correct the error
            return render(request, 'camera_config_form.html')

    # Render the camera configuration form for GET requests
    return render(request, 'camera/camera_config_form.html')


# READ: Function to list all camera configurations
@login_required
@user_passes_test(is_admin)
def camera_config_list(request):
    # Retrieve all CameraConfiguration objects from the database
    configs = CameraConfiguration.objects.all()
    # Render the list template with the retrieved configurations
    return render(request, 'camera/camera_config_list.html', {'configs': configs})


# UPDATE: Function to edit an existing camera configuration
@login_required
@user_passes_test(is_admin)
def camera_config_update(request, pk):
    # Retrieve the specific configuration by primary key or return a 404 error if not found
    config = get_object_or_404(CameraConfiguration, pk=pk)

    # Check if the request method is POST, indicating form submission
    if request.method == "POST":
        # Update the configuration fields with data from the form
        config.name = request.POST.get('name')
        config.camera_source = request.POST.get('camera_source')
        config.threshold = request.POST.get('threshold')
        config.success_sound_path = request.POST.get('success_sound_path')

        # Save the changes to the database
        config.save()  

        # Redirect to the list page after successful update
        return redirect('camera_config_list')  
    
    # Render the configuration form with the current configuration data for GET requests
    return render(request, 'camera/camera_config_form.html', {'config': config})


# DELETE: Function to delete a camera configuration
@login_required
@user_passes_test(is_admin)
def camera_config_delete(request, pk):
    # Retrieve the specific configuration by primary key or return a 404 error if not found
    config = get_object_or_404(CameraConfiguration, pk=pk)

    # Check if the request method is POST, indicating confirmation of deletion
    if request.method == "POST":
        # Delete the record from the database
        config.delete()  
        # Redirect to the list of camera configurations after deletion
        return redirect('camera_config_list')

    # Render the delete confirmation template with the configuration data
    return render(request, 'camera/camera_config_delete.html', {'config': config})



######################## start Student views  ####################################

# View to add a new email configuration
def add_email_config(request):
    if request.method == 'POST':
        email_host = request.POST.get('email_host')
        email_port = request.POST.get('email_port')
        email_use_tls = request.POST.get('email_use_tls') == 'on'
        email_host_user = request.POST.get('email_host_user')
        email_host_password = request.POST.get('email_host_password')

        # Create and save the new EmailConfig instance
        EmailConfig.objects.create(
            email_host=email_host,
            email_port=email_port,
            email_use_tls=email_use_tls,
            email_host_user=email_host_user,
            email_host_password=email_host_password
        )

        messages.success(request, "Email configuration added successfully.")
        return redirect('view_email_configs')  # Redirect to view the email configs

    return render(request, 'email/add_email_config.html')

# View to edit an existing email configuration
def edit_email_config(request, email_config_id):
    email_config = get_object_or_404(EmailConfig, id=email_config_id)

    if request.method == 'POST':
        email_config.email_host = request.POST.get('email_host')
        email_config.email_port = request.POST.get('email_port')
        email_config.email_use_tls = request.POST.get('email_use_tls') == 'on'
        email_config.email_host_user = request.POST.get('email_host_user')
        email_config.email_host_password = request.POST.get('email_host_password')

        email_config.save()
        messages.success(request, "Email configuration updated successfully.")
        return redirect('view_email_configs')  # Redirect to view the email configs

    return render(request, 'email/edit_email_config.html', {'email_config': email_config})

# View to delete an email configuration
def delete_email_config(request, email_config_id):
    email_config = get_object_or_404(EmailConfig, id=email_config_id)
    email_config.delete()
    messages.success(request, "Email configuration deleted successfully.")
    return redirect('view_email_configs')  # Redirect to view the email configs

# View to list all email configurations
def view_email_configs(request):
    email_configs = EmailConfig.objects.all()
    return render(request, 'email/view_email_configs.html', {'email_configs': email_configs})


###################################################################################


# Department Views
def department_list(request):
    departments = Department.objects.all()
    return render(request, 'department_list.html', {'departments': departments})

def department_create(request):
    if request.method == "POST":
        name = request.POST['name']
        description = request.POST.get('description', '')
        Department.objects.create(name=name, description=description)
        return redirect('department_list')
    return render(request, 'department_form.html')

def department_update(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        department.name = request.POST['name']
        department.description = request.POST.get('description', '')
        department.save()
        return redirect('department_list')
    return render(request, 'department_form.html', {'department': department})

def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == "POST":
        department.delete()
        return redirect('department_list')
    return render(request, 'department_confirm_delete.html', {'department': department})



##############################################################################

from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect, render

def create_settings(request):
    students = Student.objects.all()
    if request.method == 'POST':
        student_id = request.POST.get('student')
        check_out_time_threshold = request.POST.get('check_out_time_threshold')

        student = Student.objects.get(id=student_id) if student_id else None

        # Check if settings already exist for the selected student
        if student and Settings.objects.filter(student=student).exists():
            messages.error(request, f"Check-out Threshold  for student '{student.name}' already exist.")
            return redirect('create_settings')

        # Create new settings
        try:
            Settings.objects.create(
                student=student, 
                check_out_time_threshold=check_out_time_threshold
            )
            # Success message
            messages.success(request, "Settings created successfully!")
        except IntegrityError:
            messages.error(request, "An error occurred while saving the settings. Please try again.")
            return redirect('create_settings')

        return redirect('settings_list')

    return render(request, 'settings_form.html', {'students': students})



# Read settings (list view)
def settings_list(request):
    settings = Settings.objects.all()
    for setting in settings:
        time_in_seconds = setting.check_out_time_threshold

        if time_in_seconds < 60:
            setting.formatted_time = f"{time_in_seconds} seconds"
        elif time_in_seconds < 3600:
            minutes = time_in_seconds // 60
            setting.formatted_time = f"{minutes} minutes"
        else:
            hours = time_in_seconds // 3600
            setting.formatted_time = f"{hours} hours"

    return render(request, 'settings_list.html', {'settings': settings})

# Update settings
def update_settings(request, pk):
    settings = get_object_or_404(Settings, pk=pk)
    
    if request.method == 'POST':
        student_id = request.POST.get('student')
        check_out_time_threshold = request.POST.get('check_out_time_threshold', 60)
        
        settings.student = get_object_or_404(Student, id=student_id) if student_id else None
        settings.check_out_time_threshold = check_out_time_threshold
        settings.save()
        return redirect('settings_list')
    
    students = Student.objects.all()
    return render(request, 'settings_form.html', {'settings': settings, 'students': students})

# Delete settings
def delete_settings(request, pk):
    settings = get_object_or_404(Settings, pk=pk)
    if request.method == 'POST':
        settings.delete()
        return redirect('settings_list')
    return render(request, 'settings_confirm_delete.html', {'settings': settings})
