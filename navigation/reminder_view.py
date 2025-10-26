from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from .models import Reminder
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

def reminder(request):
    if not request.session.get('user_roll_number'):
        return redirect('login')
    if request.method == 'POST':
        reminder_text = request.POST.get('reminder_text', '').strip()
        reminder_date_str = request.POST.get('reminder_date', '').strip()
        if reminder_text and reminder_date_str:
            try:
                reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%d %H:%M')
                reminder_date = timezone.make_aware(reminder_date, timezone.get_current_timezone())
                if reminder_date > timezone.now():
                    Reminder.objects.create(
                        roll_number=request.session['user_roll_number'],
                        reminder_text=reminder_text,
                        reminder_date=reminder_date
                    )
                    messages.success(request, 'Reminder added successfully!')
                else:
                    messages.error(request, 'Reminder date must be in the future.')
            except ValueError:
                messages.error(request, 'Invalid date format. Use YYYY-MM-DD HH:MM.')
        else:
            messages.error(request, 'Reminder text and date are required.')
        return redirect('reminder')
    reminders = Reminder.objects.filter(roll_number=request.session['user_roll_number']).order_by('reminder_date')
    reminders_data = [
        {
            'id': r.id,
            'text': r.reminder_text,
            'date': r.reminder_date.isoformat(),
            'created_at': r.created_at.isoformat()
        } for r in reminders
    ]
    return render(request, 'navigation/reminder.html', {'reminders': reminders, 'reminders_data': json.dumps(reminders_data)})

@require_http_methods(["DELETE"])
def delete_reminder(request, reminder_id):
    if not request.session.get('user_roll_number'):
        return JsonResponse({'error': 'Not authenticated'}, status=403)
    try:
        reminder = Reminder.objects.get(id=reminder_id, roll_number=request.session['user_roll_number'])
        reminder.delete()
        return JsonResponse({'message': 'Reminder deleted'}, status=200)
    except Reminder.DoesNotExist:
        return JsonResponse({'error': 'Reminder not found'}, status=404)