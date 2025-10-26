import folium
from fuzzywuzzy import process
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import AppUser
import json
import os

# Create your views here.

Coordinates_list = {
    "vsbhostel": ("22.531799", "75.923740"), "vsb": ("22.531799", "75.923740"),
    "hjbhostel": ("22.532027", "75.924920"), "hjb": ("22.532027", "75.924920"),
    "cvrhostel": ("22.532418", "75.924100"), "cvr": ("22.532418", "75.924100"),
    "dahostel": ("22.531091", "75.923477"), "da": ("22.531091", "75.923477"),
    "apjhostel": ("22.530649", "75.924293"), "apj": ("22.530649", "75.924293"),
    "jcbhostel": ("22.527647", "75.925087"), "jcb": ("22.527647", "75.925087"),
    "healthcentre": ("22.525538", "75.926304"), "hospital": ("22.525538", "75.926304"),
    "lrc": ("22.528980", "75.922651"), "learningresourcecentre": ("22.528980", "75.922651"),
    "busstop": ("22.528980", "75.922651"),
    "nescafe": ("22.528662", "75.923880"),
    "dominos": ("22.528717", "75.924604"),
    "lafresco": ("22.530310", "75.922997"),
    "narmadahallofresidence": ("22.523546", "75.922418"), "narmada": ("22.523546", "75.922418"),
    "kshiprahallofresidence": ("22.522986", "75.925342"), "kshipra": ("22.522986", "75.925342"),
    "shribalhanumanmandir": ("22.531766", "75.920570"), "mandir": ("22.531766", "75.920570"),
    "masjid": ("22.531766", "75.920570"),
    "sportscomplex": ("22.531766", "75.920570"),
    "abhinandanbhavan": ("22.528392", "75.921498"),
    "centralworkshop": ("22.525890", "75.921361"),
    "citc": ("22.525479", "75.921723"),
    "hvacplant": ("22.525479", "75.921723"),
    "sewagetreatmentplant": ("22.535066", "75.929185"),
    "maalaundry": ("22.535066", "75.929185"), "laundry": ("22.535066", "75.929185"),
    "cyclerepairshop": ("22.532453", "75.921426"),
    "gate1a": ("22.529529", "75.912679"),
    "gate1b": ("22.528566", "75.917104"),
    "gate2": ("22.51901", "75.91561"),
    "nalandaauditorium": ("22.526413", "75.924341"), "lhc": ("22.526413", "75.924341"),
    "lecturehallcomplex": ("22.526413", "75.924341"),
    "takshilla": ("22.526413", "75.924341"),
    "vikramshilla": ("22.526413", "75.924341"),
    "pod1b": ("22.529405", "75.924169"),
    "pod1a": ("22.529058", "75.924502"),
    "pod1c": ("22.529388", "75.923327"),
    "pod1d": ("22.529091", "75.923440"),
    "pod1e": ("22.528833", "75.923469"),
    "amul": ("22.5296329", "75.9252789"),
    "jucilicious": ("22.5294523", "75.9251020"), "juicy": ("22.5294523", "75.9251020"),
    "centraldinninghall": ("22.528975", "75.925320"), "mess": ("22.528975", "75.925320"),
    "shirucafe": ("22.5298652", "75.9248066"),
    "ascanteen": ("22.5305232", "75.9251028"),
    "villagecafe": ("22.5301604", "75.9248613"),
    "zippycafe": ("22.5302921", "75.9250271"),
    "vindhyachalguesthouse": ("22.524173", "75.925806"), "guesthouse": ("22.524173", "75.925806"),
    "kendriyavidyalay": ("22.520518", "75.921179"), "kv": ("22.520518", "75.921179"),
    "sic": ("22.521581", "75.921275"),
    "directorbungalow": ("22.519991", "75.923220"),
    "ravechi": ("22.528719", "75.922541"),
    "dailyneeds": ("22.529453", "75.925443"), "dn": ("22.529453", "75.925443"),
    "fruitsshop": ("22.5302106", "75.9229220"),
    "parkingnalanda": ("22.526581", "75.923558"),
    "parkinglrc": ("22.528147", "75.922847"),
    "parkingpod": ("22.528110", "75.924725"),
    "parkinghc": ("22.525630", "75.926060"),
    "parkingsportscomplex": ("22.529906", "75.920111"),
    "canarabank": ("22.5303037", "75.9228661"),
    "sbiatm": ("22.5253889", "75.9210500")
}

word_list = list(Coordinates_list.keys())

def autocorrect(word, wordlist):
    return process.extractOne(word, wordlist)[0] if word else None

def navigation_home(request):
    if not request.session.get('user_roll_number'):
        return redirect('login')
    return render(request, 'navigation/navigation.html', {'locations': word_list})

@csrf_exempt
def get_map(request):
    print("Received request:", request.body)
    if request.method == 'POST' and request.session.get("user_roll_number"):
        try:
            data = json.loads(request.body)
            print("Parsed data:", data)
            start_location = data.get("start", "").lower().replace(" ", "")
            end_location = data.get("end", "").lower().replace(" ", "")

            if not start_location or not end_location:
                return JsonResponse({"error": "Start and end locations are required"}, status=400)

            start_location = autocorrect(start_location, word_list)
            end_location = autocorrect(end_location, word_list)

            if not start_location or not end_location:
                return JsonResponse({"error": "Invalid location(s) provided"}, status=400)

            start_coords = Coordinates_list[start_location]
            end_coords = Coordinates_list[end_location]

            map_obj = folium.Map(location=[float(start_coords[0]), float(start_coords[1])], zoom_start=15)
            folium.Marker([float(start_coords[0]), float(start_coords[1])], tooltip=f"Start: {start_location}").add_to(map_obj)
            folium.Marker([float(end_coords[0]), float(end_coords[1])], tooltip=f"End: {end_location}").add_to(map_obj)

            map_path = os.path.join(settings.STATICFILES_DIRS[0], 'maps', 'map.html')
            os.makedirs(os.path.dirname(map_path), exist_ok=True)
            map_obj.save(map_path)

            return JsonResponse({"message": "Map generated", "map_url": "/static/maps/map.html"})
        except Exception as e:
            print("Error:", str(e))
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method or not authenticated"}, status=405)

def signup(request):
    if request.method == 'POST':
        roll_number = request.POST['roll_number']
        password = request.POST['password']
        print(f"Signing up with roll_number: {roll_number}, password: {password}")  # Debug
        if AppUser.objects.filter(roll_number=roll_number).exists():
            messages.error(request, 'Roll number already exists.')
        else:
            AppUser.objects.create(roll_number=roll_number, password=password)
            print(f"User created: {roll_number}, {password}")  # Debug
            messages.success(request, 'Account created successfully!')
        return redirect('login')
    return render(request, 'navigation/signup.html')

def login_view(request):
    if request.method == 'POST':
        roll_number = request.POST['roll_number']
        password = request.POST['password']
        # print(f"Attempting login for roll_number: {roll_number}, password: {password}")  # Debug
        user = AppUser.objects.filter(roll_number=roll_number, password=password).first()
        # print(f"User query result: {user}")  # Debug
        if user:
            request.session['user_roll_number'] = roll_number
            request.session.save()
            print("Login successful, redirecting to navigation_home")  # Debug
            return redirect('home')
        else:
            messages.error(request, 'Invalid roll number or password.')
            print("Login failed - No matching user")  # Debug
    return render(request, 'navigation/login.html')

def logout_view(request):
    logout(request)
    return redirect('login')
