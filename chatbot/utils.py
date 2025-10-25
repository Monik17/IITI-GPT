# chatbot/utils.py
import logging
from langchain.schema import Document
from langgraph.graph import StateGraph, END, START
from .models import GraphState
from langchain_community.tools.tavily_search import TavilySearchResults

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Placeholder for LLM and tools (to be configured with Cohere)
from langchain_community.llms import Cohere
from langchain.prompts import ChatPromptTemplate
from django.conf import settings

llm = Cohere(cohere_api_key=settings.COHERE_API_KEY)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Answer the question based on the context."),
    ("human", "{question}")
])
llm_chain = prompt | llm

# Dummy implementations (replace with actual vectorstore and web search tools)
# def retrieve(state):
#     logger.info("---RETRIEVE---")
#     question = state.question
#     # Placeholder: Replace with actual vectorstore retrieval
#     documents = [Document(page_content=f"Mock document for {question}")]
#     return GraphState.from_dict({"question": question, "documents": documents})

def generate(state):
    logger.info("---GENERATE---")
    question = state.question
    documents = state.documents
    generation = llm_chain.invoke({"question": question}).content
    return GraphState.from_dict({"question": question, "documents": documents, "generation": generation})

def web_search(state):
    logger.info("---WEB SEARCH---")
    question = state.question
    
    web_search_tool = TavilySearchResults(k=3, tavily_api_key="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")
    docs = web_search_tool.invoke({"query": question})

    # docs = [Document(page_content=f"Web result for {question} from IIT Indore site")]
    return GraphState.from_dict({"question": question, "documents": docs})

def grade_documents(state):
    logger.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state.question
    documents = state.documents or []
    filtered_docs = documents  # Placeholder: Implement grading logic
    return GraphState.from_dict({"question": question, "documents": filtered_docs})

def route_question(state):
    logger.info("---ROUTE QUESTION---")
    question = state.question
    # Placeholder: Implement router logic
    return "web_search"  # Default to web search for now

def decide_to_generate(state):
    logger.info("---ASSESS GRADED DOCUMENTS---")
    documents = state.documents
    return "generate" if documents else "web_search"

# Build the graph
workflow = StateGraph(GraphState)
workflow.add_node("web_search", web_search)
# workflow.add_node("retrieve", retrieve)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_conditional_edges(START, route_question, {"web_search": "web_search"})
workflow.add_edge("web_search", "generate")
workflow.compile()