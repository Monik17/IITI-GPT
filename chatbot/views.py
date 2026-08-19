# chatbot/views.py
from django.shortcuts import render
from django.http import JsonResponse

from .utils import workflow


# @login_required
def chatbot_view(request):
    if not request.session.get("user_roll_number"):
        print("here")
        return render(request, "chatbot/chatbot.html")

    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if question:
            # Get conversation history from the current Django session
            chat_history = request.session.get("chat_history", [])

            # Initial LangGraph state
            state = {
                "question": question,
                "chat_history": chat_history
            }

            # Run workflow
            for output in workflow.stream(state):
                for key, value in output.items():
                    state.update(value)

            # Get generated answer
            response = state.get(
                "generation",
                "No response available"
            )

            # Save this exchange to session history
            chat_history.append({
                "role": "user",
                "content": question
            })

            chat_history.append({
                "role": "assistant",
                "content": response
            })

            # Keep only the most recent 10 messages
            request.session["chat_history"] = chat_history[-10:]

            # Explicitly save the session
            request.session.modified = True

            return JsonResponse({
                "response": response
            })

        return JsonResponse({
            "error": "Question is required"
        }, status=400)

    return render(request, "chatbot/chatbot.html")