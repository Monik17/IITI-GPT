# 🧠 IITI-GPT

An intelligent assistant web app tailored for **IIT Indore**, integrating a conversational chatbot, user login, reminder system, and navigation. The chatbot is powered by **Cohere’s Large Language Model (LLM)** and enhanced with real-time information retrieval using the **Tavily Search API**.

![HomePage Screenshot](https://github.com/Siddharththakur3617/IITI-GPT/blob/main/assets/home_demo.jpg)
![Chatbot Screenshot](https://github.com/Siddharththakur3617/IITI-GPT/blob/main/assets/chatbot_demo2.jpg)
![Reminder Screenshot](https://github.com/Siddharththakur3617/IITI-GPT/blob/main/assets/reminder_demo.jpg)

---

## 🚀 Features

### ✅ User Authentication
- Secure login/logout functionality with session tracking.
- Redirects unauthenticated users appropriately.

### 💬 AI-Powered Chatbot
- Uses **Cohere LLM** for natural and intelligent responses.
- Integrates **Tavily Search API** for up-to-date, contextually relevant web results.
- Handles campus-specific questions (e.g., hostels, emergency numbers).

### ⏰ Smart Reminder System
- Users can create reminders with custom text and datetime.
- Stores and displays reminders with real-time notification support.

### 🧭 Navigation System
- Clean user interface with Bootstrap-based routing between Home, Chatbot, and Reminder modules.

---

## 🛠️ Tech Stack

| Category         | Technologies Used                                      |
|------------------|--------------------------------------------------------|
| **Frontend**     | HTML, CSS, JavaScript, Bootstrap                       |
| **Backend**      | Django (Python Framework)                              |
| **Database**     | SQLite (Default Django DB)                             |
| **Authentication** | Django’s built-in auth system                         |
| **Chatbot Logic**| Cohere LLM, Tavily Search API, custom routing logic    |
| **Notifications**| Browser Notification API (for reminders)               |
| **Deployment**   | Localhost / Deployable on Heroku, Render, etc.         |

---

## 🧩 Project Structure

IITI-GPT/
│
├── chatbot/ # Handles AI logic, prompts, and views
├── reminders/ # Reminder app with models and views
├── users/ # Handles user authentication
├── static/ # JS, CSS, and other static files
├── templates/ # HTML templates
├── IITI_GPT/ # Django project settings and URLs
├── db.sqlite3 # SQLite database
├── requirements.txt # Python dependencies
├── manage.py # Django management script
└── README.md # Project documentation

## 🔌 API Keys & Configuration

### 🔐 Required Keys:
- **Cohere API Key**: For LLM-powered responses.
- **Tavily Search API Key**: For web search augmentation.

### 📁 Add `.env` file:
Create a `.env` file in your root directory with the following:
```env
COHERE_API_KEY=your_cohere_key
TAVILY_API_KEY=your_tavily_key
```
## 🧪 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/Siddharththakur3617/IITI-GPT.git
cd IITI-GPT
```

### 2. Set up Virtual Environment

```bash
git clone https://github.com/Siddharththakur3617/IITI-GPT.git
cd IITI-GPT
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Run the Server

```bash
python manage.py runserver
```
Then open your browser and go to: http://127.0.0.1:8000/

## 📅 Planned Enhancements

- 🧠 **University Database Integration**  
  Connect to official IIT Indore databases for real-time, authenticated information.

- 🌐 **Multilingual Support**  
  Enable chatbot interactions in multiple Indian and global languages for wider accessibility.

- 📅 **Google Calendar Sync**  
  Automatically sync user-created reminders with their Google Calendar accounts.

- 🗣️ **Voice Interaction Features**  
  Add support for voice-based question input and text-to-speech (TTS) responses.

- 📈 **Admin Analytics Dashboard**  
  Track chatbot usage metrics, popular queries, and user engagement via a dedicated dashboard.

- 📱 **Progressive Web App (PWA)**  
  Convert the application into a mobile-friendly PWA for offline use and push notifications.

---

## 🤝 Contributors

- **Siddharth Singh** – [@Siddharththakur3617](https://github.com/Siddharththakur3617)
- **Abhitulya Mishra** – [@Abhitulya](https://github.com/Abhitulya)
