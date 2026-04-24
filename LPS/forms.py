from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import CustomerProfile

# Create a custom registration form that extends Django's built-in User Creation Form
class CustomerRegistrationForm(UserCreationForm):
    
    # Additional fields that are not included in the User
    first_name = forms.CharField(max_length = 100)
    last_name = forms.CharField(max_length = 100)
    email = forms.EmailField()
    home_address = forms.CharField(max_length = 255)
    phone_number = forms.CharField(max_length = 20)

    # Meta class telling Django which model this form is tied to
    class Meta:
        model = User # The form creates a User object
        fields = ['first_name', 'last_name', 'email', 'home_address', 'phone_number', 'username', 'password1', 'password2',]
    
    # Override the default save() method to handle extra fields
    def save(self, commit = True):

        # Call parent save but do not save to databse yet
        # This gives a User object we can modify
        user = super().save(commit = False)

        # Assign cleaned form data to the User model fields
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']

        # If comit =  True, save everything to the database
        if commit:
            user.save() # Save the User object first

            # Create a related CustomerProfile object
            # This stores extra fields not included in the User model
            CustomerProfile.objects.create(
                user = user,
                home_address = self.cleaned_data['home_address'],
                phone_number = self.cleaned_data['phone_number']
            )

        # Return the created user instance
        return user

    