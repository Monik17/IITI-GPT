from typing import TypedDict, List, Any


class GraphState(TypedDict, total=False):
    question: str
    documents: List[Any]
    generation: str