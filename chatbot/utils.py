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


# ============================================================
# 1. CHECK WHETHER CONVERSATION MEMORY IS SUFFICIENT
# ============================================================

memory_check_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a conversation-memory classifier.

Determine whether the conversation history contains enough
information to answer the user's latest message WITHOUT using
external knowledge.

Return ONLY one word:

MEMORY
or
RETRIEVE

Use MEMORY when:
- The answer can be derived from facts explicitly stated in the
  conversation.
- The user is asking about something they previously told you.
- The user is making a conversational statement that does not
  require external information.
- The user asks something like "who is X?" and X was explicitly
  described earlier in the conversation.

Use RETRIEVE when:
- The answer requires IIT Indore information not contained in
  the conversation.
- The answer requires factual external knowledge.
- The question asks for fees, admissions, facilities, policies,
  departments, etc. unless that information was explicitly
  provided in the conversation.
- The question requires current/live information.

Do not answer the question. Return only MEMORY or RETRIEVE."""
    ),
    (
        "human",
        """Conversation history:
{chat_history}

Latest user message:
{question}"""
    )
])

memory_check_chain = memory_check_prompt | llm


def check_memory(state):
    logger.info("---CHECK CONVERSATION MEMORY---")

    question = state["question"]
    chat_history = state.get("chat_history", [])

    # No history means external retrieval is required
    if not chat_history:
        logger.info("No conversation history → RETRIEVE")
        return {
            "memory_sufficient": False
        }

    history_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in chat_history
    )

    raw = memory_check_chain.invoke({
        "chat_history": history_text,
        "question": question
    })

    decision = (
        raw.content.strip().upper()
        if hasattr(raw, "content")
        else str(raw).strip().upper()
    )

    # Safety: only accept MEMORY explicitly
    memory_sufficient = decision == "MEMORY"

    logger.info(
        "Memory decision: %s",
        "MEMORY" if memory_sufficient else "RETRIEVE"
    )

    return {
        "memory_sufficient": memory_sufficient
    }


# ============================================================
# 2. QUESTION CONTEXTUALIZATION
# ============================================================

contextualize_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a question contextualizer for an IIT Indore chatbot.

Rewrite the latest user message into a standalone question when
previous conversation is necessary to understand it.

Rules:
- If the latest message is already standalone, return it unchanged.
- Resolve references such as "it", "that", "this", "they", "those",
  "previous one", etc.
- If the user provides a new statement or fact, return that statement
  unchanged.
- Do not answer the user.
- Return ONLY the rewritten question or original message."""
    ),
    (
        "human",
        """Conversation history:
{chat_history}

Latest user message:
{question}"""
    )
])

contextualize_chain = contextualize_prompt | llm


def contextualize_question(state):
    logger.info("---CONTEXTUALIZE QUESTION---")

    question = state["question"]
    chat_history = state.get("chat_history", [])

    if not chat_history:
        return {
            "question": question
        }

    history_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in chat_history
    )

    raw = contextualize_chain.invoke({
        "chat_history": history_text,
        "question": question
    })

    contextualized_question = (
        raw.content.strip()
        if hasattr(raw, "content")
        else str(raw).strip()
    )

    logger.info(
        "Contextualized question: %s",
        contextualized_question
    )

    return {
        "question": contextualized_question
    }


# ============================================================
# 3. RETRIEVAL
# ============================================================

def retrieve(state):
    logger.info("---RETRIEVE---")

    question = state["question"]

    documents = rag.retrieve_documents(question)

    return {
        "question": question,
        "documents": documents
    }


# ============================================================
# 4. WEB SEARCH
# ============================================================

def web_search(state):
    logger.info("---WEB SEARCH---")

    question = state["question"]

    web_search_tool = TavilySearchResults(
        k=3,
        tavily_api_key=settings.TAVILY_API_KEY
    )

    docs = web_search_tool.invoke({
        "query": question
    })

    return {
        "question": question,
        "documents": docs
    }


# ============================================================
# 5. DOCUMENT RELEVANCE
# ============================================================

def grade_documents(state):
    logger.info("---CHECK DOCUMENT RELEVANCE TO QUESTION---")

    documents = state.get("documents", [])

    filtered_docs = rag.filter_relevant(documents)

    return {
        "question": state["question"],
        "documents": filtered_docs
    }


# ============================================================
# 6. ROUTER
# ============================================================

def route_question(state):
    logger.info("---ROUTE QUESTION---")

    question = state["question"]

    if rag.is_recency_sensitive(question):
        logger.info(
            "Routing to web_search (recency-sensitive question)"
        )
        return "web_search"

    logger.info(
        "Routing to vectorstore (local IIT Indore knowledge base)"
    )

    return "vectorstore"


# ============================================================
# 7. DECIDE WHETHER TO GENERATE OR WEB SEARCH
# ============================================================

def decide_to_generate(state):
    logger.info("---ASSESS GRADED DOCUMENTS---")

    documents = state.get("documents", [])

    return "generate" if documents else "web_search"


# ============================================================
# 8. FINAL ANSWER GENERATION
# ============================================================

answer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are IITI-GPT, a helpful assistant for IIT Indore
students, faculty, and prospective applicants.

You have two possible information sources:

1. Conversation history
2. Retrieved context from IIT Indore or live web search

Use the conversation history when the answer is based on something
the user explicitly told you.

Use retrieved context when external/IIT Indore information is needed.

IMPORTANT:

- Always answer the CURRENT user message.
- Do not continue an old topic when the user has started a new topic.
- Treat facts explicitly provided by the user as valid conversation
  context.
- Do not claim that a user-provided fact is missing just because
  it is not present in retrieved documents.
- Never fabricate factual information.
- Never invent fees, dates, names, policies, statistics, or URLs.
- If the required information is unavailable, say so.
- Keep answers concise and useful.
- Use Markdown bullets or tables when genuinely useful.
- Do not force incomplete information into a table.
- Preserve numbers, dates, and units exactly.
- Mention relevant sources when available.

Conversation history:
{chat_history}

Retrieved context:
{context}"""
    ),
    (
        "human",
        "{question}"
    )
])

answer_chain = answer_prompt | llm


def generate(state):
    logger.info("---GENERATE---")

    question = state["question"]
    documents = state.get("documents", [])
    chat_history = state.get("chat_history", [])

    context = rag.build_context(documents)

    history_text = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in chat_history
    )

    raw = answer_chain.invoke({
        "question": question,
        "context": context,
        "chat_history": history_text
    })

    generation = (
        raw.content
        if hasattr(raw, "content")
        else str(raw)
    )

    return {
        "question": question,
        "documents": documents,
        "generation": generation
    }


# ============================================================
# 9. BUILD LANGGRAPH
# ============================================================

workflow = StateGraph(GraphState)

workflow.add_node(
    "check_memory",
    check_memory
)

workflow.add_node(
    "contextualize_question",
    contextualize_question
)

workflow.add_node(
    "retrieve",
    retrieve
)

workflow.add_node(
    "web_search",
    web_search
)

workflow.add_node(
    "grade_documents",
    grade_documents
)

workflow.add_node(
    "generate",
    generate
)


# START → MEMORY CHECK
workflow.add_edge(
    START,
    "check_memory"
)


# MEMORY CHECK
def route_after_memory(state):
    if state.get("memory_sufficient", False):
        logger.info(
            "Conversation memory is sufficient → GENERATE"
        )
        return "generate"

    logger.info(
        "Conversation memory insufficient → CONTEXTUALIZE"
    )
    return "contextualize"


workflow.add_conditional_edges(
    "check_memory",
    route_after_memory,
    {
        "generate": "generate",
        "contextualize": "contextualize_question"
    }
)


# CONTEXTUALIZE → CHROMA/TAVILY ROUTER
workflow.add_conditional_edges(
    "contextualize_question",
    route_question,
    {
        "vectorstore": "retrieve",
        "web_search": "web_search",
    }
)


# CHROMA
workflow.add_edge(
    "retrieve",
    "grade_documents"
)


workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "generate": "generate",
        "web_search": "web_search",
    }
)


# TAVILY
workflow.add_edge(
    "web_search",
    "generate"
)


# GENERATE → END
workflow.add_edge(
    "generate",
    END
)


workflow = workflow.compile()