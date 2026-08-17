# chatbot/utils.py
import logging

from django.conf import settings
from langchain.prompts import ChatPromptTemplate
from langchain_cohere import ChatCohere
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END, START

from . import rag
from .models import GraphState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

llm = ChatCohere(
    cohere_api_key=settings.COHERE_API_KEY,
    model="command-a-03-2025"
)

# {context} carries retrieved/searched documents into the prompt — the
# original prompt only had {question}, so fetched documents never actually
# reached the LLM.
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are IITI-GPT, a helpful assistant for IIT Indore students, faculty, "
     "and prospective applicants. Answer the question using ONLY the context "
     "provided below. If the context doesn't contain the answer, say you don't "
     "have that information rather than guessing. Keep answers concise, and "
     "mention the source URL when it's useful for the user to verify.\n\n"
     "Context:\n{context}"),
    ("human", "{question}")
])
llm_chain = prompt | llm

def retrieve(state):
    logger.info("---RETRIEVE---")
    question = state["question"]
    documents = rag.retrieve_documents(question)
    return {
        "question": question,
        "documents": documents
    }


def web_search(state):
    logger.info("---WEB SEARCH---")
    question = state["question"]

    web_search_tool = TavilySearchResults(
        k=3,
        tavily_api_key=settings.TAVILY_API_KEY
    )

    docs = web_search_tool.invoke({"query": question})

    return {
        "question": question,
        "documents": docs
    }


def grade_documents(state):
    logger.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state.get("documents", [])

    filtered_docs = rag.filter_relevant(documents)

    return {
        "question": question,
        "documents": filtered_docs
    }


def route_question(state):
    logger.info("---ROUTE QUESTION---")
    question = state["question"]
    if rag.is_recency_sensitive(question):
        logger.info("Routing to web_search (recency-sensitive question)")
        return "web_search"
    logger.info("Routing to vectorstore (local IIT Indore knowledge base)")
    return "vectorstore"


def decide_to_generate(state):
    logger.info("---ASSESS GRADED DOCUMENTS---")
    documents = state.get("documents", [])
    return "generate" if documents else "web_search"


def generate(state):
    logger.info("---GENERATE---")
    question = state["question"]
    documents = state.get("documents", [])

    context = rag.build_context(documents)

    raw = llm_chain.invoke({
        "question": question,
        "context": context
    })

    generation = raw.content if hasattr(raw, "content") else raw

    return {
        "question": question,
        "documents": documents,
        "generation": generation
    }

# --- Build the graph ---
#
#          START
#            |
#     route_question
#        /        \
#  vectorstore    web_search
#       |              \
#   retrieve             \
#       |                  \
# grade_documents            \
#    /       \                 \
# generate  web_search --------> generate
#               |                    |
#              END <-----------------+
#
workflow = StateGraph(GraphState)
workflow.add_node("retrieve", retrieve)
workflow.add_node("web_search", web_search)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)

# Route each question to either the local vector DB or a live web search...
workflow.add_conditional_edges(START, route_question, {
    "vectorstore": "retrieve",
    "web_search": "web_search",
})
# ...local retrieval gets graded for relevance, falling back to web_search
# if nothing relevant enough was found locally...
workflow.add_edge("retrieve", "grade_documents")
workflow.add_conditional_edges("grade_documents", decide_to_generate, {
    "generate": "generate",
    "web_search": "web_search",
})
# ...web_search results go straight to generate (already fresh, no local grading needed).
workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", END)
workflow = workflow.compile()
