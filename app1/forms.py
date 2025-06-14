from django import forms
from .models import LateCheckInPolicy
from django.core.exceptions import ValidationError
from django import forms
from django import forms
from .models import Student , CutOffPolicy

class LateCheckInPolicyForm(forms.ModelForm):
    class Meta:
        model = LateCheckInPolicy
        fields = ['student', 'start_time', 'description']
        widgets = {
            'start_time': forms.TimeInput(format='%H:%M', attrs={'type': 'time'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class CutOffPolicyForm(forms.ModelForm):
    class Meta:
        model = CutOffPolicy
        fields = ['student', 'cutoff_time', 'description']
        widgets = {
            'cutoff_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        policy_id = self.instance.id  # Get the current instance's ID

        # Check if a LateCheckInPolicy already exists for this student, excluding the current instance
        if student and CutOffPolicy.objects.filter(student=student).exclude(id=policy_id).exists():
            raise ValidationError(f"A cut off policy already exists for {student.name}.")
        
        return cleaned_data


##############################################################
from django import forms
from .models import Student
import json

class StudentEditForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            'name',
            'email',
            'phone_number',
            'face_embedding',
            'roll_no',
            'address',
            'date_of_birth',
            'joining_date',
            'mother_name',
            'father_name',
            'authorized',
            'department',
          
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'}),
            'face_embedding': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter face embedding as JSON',
            }),
            'roll_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter roll number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter address'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Enter mother's name"}),
            'father_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Enter father's name"}),
            'authorized': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'department': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }

    def clean_face_embedding(self):
        data = self.cleaned_data.get('face_embedding')
        try:
            # Ensure valid JSON data
            return json.loads(data)
        except (ValueError, TypeError):
            raise forms.ValidationError("Invalid JSON format for face embedding.")



##################################################################
