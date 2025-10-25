# chatbot/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .utils import workflow, GraphState  # Import GraphState explicitly

# @login_required
def chatbot_view(request):
    if not request.session.get("user_roll_number"):
        print("here")
        return render(request, "chatbot/chatbot.html")
    if request.method == "POST" :
        question = request.POST.get("question", "").strip()
        if question:
            # Initialize GraphState instance
            state = GraphState()
            state.question = question
            # Invoke the workflow with the state dictionary
            for output in workflow.stream(state.to_dict()):
                for key, value in output.items():
                    state = GraphState.from_dict(value)  # Update state from output
            return JsonResponse({"response": state.generation or "No response available"})
        return JsonResponse({"error": "Question is required"}, status=400)
    return render(request, "chatbot/chatbot.html")