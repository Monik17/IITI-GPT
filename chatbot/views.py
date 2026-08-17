# chatbot/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from .utils import workflow


# @login_required
def chatbot_view(request):
    if not request.session.get("user_roll_number"):
        print("here")
        return render(request, "chatbot/chatbot.html")

    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if question:
            # Initial LangGraph state
            state = {
                "question": question
            }

            # Run the workflow and collect the state updates
            for output in workflow.stream(state):
                for key, value in output.items():
                    state.update(value)

            return JsonResponse({
                "response": state.get("generation", "No response available")
            })

        return JsonResponse({
            "error": "Question is required"
        }, status=400)

    return render(request, "chatbot/chatbot.html")