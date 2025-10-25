from django.db import models
from langchain.schema import Document

# Create your models here.

class GraphState:
    def __init__(self):
        self.question = None
        self.documents = None
        self.generation = None

    def to_dict(self):
        return {
            "question": self.question,
            "documents": self.documents,
            "generation": self.generation
        }

    @classmethod
    def from_dict(cls, data):
        state = cls()
        state.question = data.get("question")
        state.documents = data.get("documents")
        state.generation = data.get("generation")
        return state