from django.db import models

# Create your models here.

class AppUser(models.Model):
    roll_number = models.CharField(max_length=20, primary_key=True)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.roll_number
    
class Reminder(models.Model):
    roll_number = models.CharField(max_length=20)
    reminder_text = models.TextField()
    reminder_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.roll_number} - {self.reminder_text}"