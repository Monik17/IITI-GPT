from django.shortcuts import render, redirect

def home(request):
    if not request.session.get('user_roll_number'):
        return redirect('login')
    return render(request, 'navigation/home.html')