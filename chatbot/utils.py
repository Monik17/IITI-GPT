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

llm = ChatCohere(cohere_api_key=settings.COHERE_API_KEY, model="command-a-03-2025")

# ============================================================
# 1. CHECK WHETHER CONVERSATION MEMORY IS SUFFICIENT
# ============================================================

memory_check_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a conversation-memory classifier.

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

Do not answer the question. Return only MEMORY or RETRIEVE."""),
    ("human", """Conversation history:
{chat_history}

Latest user message:
{question}""")
])

memory_check_chain = memory_check_prompt | llm

def check_memory(state):
    logger.info("---CHECK CONVERSATION MEMORY---")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    if not chat_history:
        logger.info("No conversation history → RETRIEVE")
        return {"memory_sufficient": False}

    history_text = "\n".join(
        f"{message['role']}: {message['content']}" for message in chat_history
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

    memory_sufficient = decision == "MEMORY"

    logger.info(
        "Memory decision: %s",
        "MEMORY" if memory_sufficient else "RETRIEVE"
    )

    return {"memory_sufficient": memory_sufficient}


# ============================================================
# 2. QUESTION CONTEXTUALIZATION
# ============================================================

contextualize_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a question contextualizer for an IIT Indore chatbot.

Rewrite the latest user message into a standalone question when
previous conversation is necessary to understand it.

Rules:
- If the latest message is already standalone, return it unchanged.
- Resolve references such as "it", "that", "this", "they", "those",
  "previous one", etc.
- If the user provides a new statement or fact, return that statement
  unchanged.
- Do not answer the user.
- Return ONLY the rewritten question or original message."""),
    ("human", """Conversation history:
{chat_history}

Latest user message:
{question}""")
])

contextualize_chain = contextualize_prompt | llm

def contextualize_question(state):
    logger.info("---CONTEXTUALIZE QUESTION---")
    question = state["question"]
    chat_history = state.get("chat_history", [])

    if not chat_history:
        return {"question": question}

    history_text = "\n".join(
        f"{message['role']}: {message['content']}" for message in chat_history
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

    logger.info("Contextualized question: %s", contextualized_question)

    return {"question": contextualized_question}


# ============================================================
# 3. LLM QUESTION ROUTER
# ============================================================

router_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are the routing classifier for IITI-GPT.

Your job is to decide where the user's question should be answered from.

Choose exactly ONE:

RAG
WEB

Choose RAG when:
- The question is about IIT Indore's relatively stable information.
- The local IIT Indore knowledge base is likely to contain the answer.
- The question concerns IIT Indore programs, departments, admissions,
  fees, faculty, research, campus facilities, rules, courses,
  infrastructure, or institutional information.
- The question does not require information that changes frequently.

Choose WEB when:
- The question requires current or recent information.
- The user asks about today, currently, latest, recent, this week,
  this month, live information, breaking news, or current events.
- The information is likely to have changed after the local knowledge
  base was created.
- The question asks about current weather, current announcements,
  current events, recent news, or other time-sensitive information.
- The question is about a topic outside the IIT Indore knowledge base
  where fresh web information is more appropriate.

Important:
- Prefer RAG for IIT Indore institutional questions when current
  information is not explicitly required.
- Prefer WEB when freshness is important.
- Do not answer the question.
- Return ONLY RAG or WEB.
"""),
    ("human", """User question:
{question}""")
])

router_chain = router_prompt | llm

# ============================================================
# 3. RETRIEVAL
# ============================================================

def retrieve(state):
    logger.info("---RETRIEVE---")
    question = state["question"]
    documents = rag.retrieve_documents(question)
    return {"question": question, "documents": documents}


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

    docs = web_search_tool.invoke({"query": question})
    return {"question": question, "documents": docs}


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
# RAG ANSWERABILITY CHECK
# ============================================================

answerability_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an answerability checker for an IIT Indore chatbot.

Determine whether the retrieved context contains enough factual
information to answer the user's question.

Rules:
- Answer YES only if the context contains enough information to
  directly answer the question.
- Answer NO if the context is unrelated, only partially relevant,
  too vague, or does not contain the requested information.
- Do not use outside knowledge.
- Do not try to answer the question.
- Return ONLY one word: YES or NO.
"""
    ),
    (
        "human",
        """Question:
{question}

Retrieved context:
{context}

Can the question be answered using ONLY this context?

Answer YES or NO."""
    )
])

answerability_chain = answerability_prompt | llm


def check_rag_answerability(state):
    logger.info("---CHECK RAG ANSWERABILITY---")

    question = state["question"]
    documents = state.get("documents", [])

    # No documents means RAG definitely cannot answer.
    if not documents:
        logger.info(
            "No RAG documents → WEB SEARCH"
        )

        return {
            "question": question,
            "rag_answerable": False
        }

    context = rag.build_context(documents)

    raw = answerability_chain.invoke({
        "question": question,
        "context": context
    })

    decision = (
        raw.content.strip().upper()
        if hasattr(raw, "content")
        else str(raw).strip().upper()
    )

    # Be strict. Only an explicit YES counts as answerable.
    answerable = decision == "YES"

    logger.info(
        "RAG answerability decision: %s",
        "ANSWERABLE" if answerable else "NOT ANSWERABLE"
    )

    return {
        "question": question,
        "documents": documents,
        "rag_answerable": answerable
    }


def decide_after_answerability(state):
    if state.get("rag_answerable", False):
        logger.info(
            "RAG context can answer question → GENERATE"
        )
        return "generate"

    logger.info(
        "RAG context cannot answer question → WEB SEARCH"
    )
    return "web_search"


# ============================================================
# 6. ROUTER
# ============================================================

def route_question(state):
    logger.info("---LLM ROUTE QUESTION---")
    question = state["question"]

    raw = router_chain.invoke({"question": question})

    decision = (
        raw.content.strip().upper()
        if hasattr(raw, "content")
        else str(raw).strip().upper()
    )

    if "WEB" in decision:
        decision = "WEB"
    else:
        decision = "RAG"

    logger.info("LLM routing decision: %s", decision)

    if decision == "WEB":
        logger.info("Routing to Tavily web search")
        return "web_search"

    logger.info("Routing to local ChromaDB RAG")
    return "vectorstore"


# ============================================================
# 7. DECIDE WHETHER TO GENERATE OR WEB SEARCH
# ============================================================

def decide_to_generate(state):
    logger.info("---ASSESS GRADED DOCUMENTS---")

    documents = state.get("documents", [])

    if not documents:
        logger.info(
            "No sufficiently relevant RAG documents → WEB SEARCH"
        )
        return "web_search"

    logger.info(
        "Relevant RAG documents found (%d) → GENERATE",
        len(documents)
    )

    return "generate"


# ============================================================
# 8. FINAL ANSWER GENERATION
# ============================================================

answer_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are IITI-GPT, a helpful assistant for IIT Indore
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
{context}"""),
    ("human", "{question}")
])

answer_chain = answer_prompt | llm

def generate(state):
    logger.info("---GENERATE---")
    question = state["question"]
    documents = state.get("documents", [])
    chat_history = state.get("chat_history", [])

    context = rag.build_context(documents)

    history_text = "\n".join(
        f"{message['role']}: {message['content']}" for message in chat_history
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

workflow.add_node("check_memory", check_memory)
workflow.add_node("contextualize_question", contextualize_question)
workflow.add_node("retrieve", retrieve)
workflow.add_node("web_search", web_search)
workflow.add_node("grade_documents", grade_documents)
workflow.add_node("generate", generate)
workflow.add_node(
    "check_rag_answerability",
    check_rag_answerability
)
workflow.add_edge(START, "check_memory")

def route_after_memory(state):
    if state.get("memory_sufficient", False):
        logger.info("Conversation memory is sufficient → GENERATE")
        return "generate"

    logger.info("Conversation memory insufficient → CONTEXTUALIZE")
    return "contextualize"

workflow.add_conditional_edges(
    "check_memory",
    route_after_memory,
    {
        "generate": "generate",
        "contextualize": "contextualize_question"
    }
)

workflow.add_conditional_edges(
    "contextualize_question",
    route_question,
    {
        "vectorstore": "retrieve",
        "web_search": "web_search",
    }
)

workflow.add_edge("retrieve", "grade_documents")

workflow.add_edge(
    "grade_documents",
    "check_rag_answerability"
)

workflow.add_conditional_edges(
    "check_rag_answerability",
    decide_after_answerability,
    {
        "generate": "generate",
        "web_search": "web_search",
    }
)

workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", END)

workflow = workflow.compile()
