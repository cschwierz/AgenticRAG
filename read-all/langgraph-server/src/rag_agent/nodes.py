# Description: Define Nodes, Edges and Message States
# Todo:
# prompt engineering oder model training für besseren context
# graph-framework auf stand von langgraph-server bringen
# tool / node zum ändern des document path hinzufügen
"""
================================================================================
                           MODUL: nodes.py
================================================================================

BESCHREIBUNG:
    Definiert die Nodes, Edges und Message States für den LanGraph-Workflow.

TABLE OF CONTENTS:
    1. Imports
    2. Load Config Variables
       - Prompts
       - Reflection
    3. Message State
       - Parent State
       - Subgraph State
    4. Parent Node Funktionen
       - model based Nodes
           - llm_node
           - orchestrator_node
           - classifier_node
           - reflect_node
       - function based Nodes
           - tool_node
           - command_node
           - ingest_node
           - retrieve_node
    5. Parent Edge Funktionen
       - tool_call_edge
       - strategy_edge
       - classify_edge
       - reflect_edge
    6. Subgraph Node Funktionen
       - retrieve_agent_node
    7. Subgraph Edge Funktionen
       - sub_tool_call_edge

AUTOR:           [chris]
DATUM ERSTELLT:  15.05.2026
LETZTES UPDATE:  2024-XX-XX

CHANGELOG:
    v1.0.0 (2024-XX-XX):
        - Initial release

================================================================================
"""

# --- Imports ---

from typing_extensions import TypedDict, Annotated
from langchain.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage, AnyMessage
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Overwrite
import os
import json
import re
from rag_agent.tools import *
from rag_agent.logfile_retriever import *

# --- Config ---

with open("/home/chris/LogfileAnalyzer/read-all/config/config.json", "r") as filejson:
#with open("C:\\Users\\chris\\Desktop\\read-all\\config\\config_win.json", "r") as filejson:
    config = json.load(filejson)

SYSTEM_PROMPT_PATH = config["SYSTEM_PROMPT_PATH"]
with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    SYSTEM_PROMPT = filetxt.read()

CLASSIFIER_PROMPT_PATH = config["CLASSIFIER_PROMPT_PATH"]
with open(CLASSIFIER_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    CLASSIFIER_PROMPT = filetxt.read()

REFLECT_PROMPT_PATH = config["REFLECT_PROMPT_PATH"]
with open(REFLECT_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    REFLECT_PROMPT = filetxt.read()

MAX_REFLECTIONS = config["MAX_REFLECTIONS"]#obsolete
MIN_REFLECTIONS = config["MIN_REFLECTIONS"]

RETRIEVER_PROMPT_PATH = config["RETRIEVER_PROMPT_PATH"]
with open(RETRIEVER_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    RETRIEVER_PROMPT = filetxt.read()

MANUAL_PATH = config["MANUAL_PATH"]
with open(MANUAL_PATH, "r", encoding="utf-8") as filetxt:
    MANUAL = filetxt.read()

FILES_PATH = config["FILES_PATH"]

# --- States ---

class MessageState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    # - Check Command -
    strategy: Literal["A", "B", "C"]
    # - Reflect -
    final_answer: bool
    # - Classifier -
    classify: Literal["A", "B", "C"]
    classify_override: bool
    # - Logfile Retriever -
    file_path: str
    lines: list
    headers: list

class RetrieveGraphState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    isolated_context: Annotated[list[AnyMessage], add_messages]
    lines: list
    headers: list
    final_answer: bool

# --- Parent Nodes ---

# - Models -

def llm_node(state: MessageState):
    """just LLM"""

    print(f"\n[DEBUG nodes.py llm_node] node invoked")

    system_message = SystemMessage(content=f"You are a helpful assistant and a expert in robotics")#todo prompt engineering for Strategy A and B
    full_messages = [system_message] + state["messages"]
    
    response_messages = model.invoke(full_messages)

    if not isinstance(response_messages, list):
        response_messages = [response_messages]

    return {"messages": response_messages, "llm_node": state.get('llm_node', 0) +1}

def orchestrator_node(state: MessageState):
    """LLM decides whether to call a tool or not"""

    print(f"\n[DEBUG nodes.py orchestrator_node] node invoked")

    history = state["messages"]
    has_plan = any("Plan:" in m.content for m in history if hasattr(m, 'content'))
    plan_instruction = "Follow the existing plan." if has_plan else "Create a new plan.\n PLAN:"

    system_message = SystemMessage(content=f"{SYSTEM_PROMPT}\n\n{plan_instruction}")
    full_messages = [system_message] + state["messages"]

    response_messages = orchestrator_model.invoke(full_messages)
    
    if not isinstance(response_messages, list):
        response_messages = [response_messages]

    return {"messages": response_messages, "orchestrator_node": state.get('orchestrator_node', 0) +1}

def classifier_node(state: MessageState):
    """LLM decides where to route the message."""

    print(f"\n[DEBUG nodes.py classifier_node] node invoked")

    if state.get("classify_override"):
        print(f"\n[DEBUG nodes.py classifier_node] classify override: {state.get("classify")}")
        return{"classify_override": False}
    
    if not state.get("file_path"):
        info_message = AIMessage(content="Info: No Logfile loaded yet. retrieval is disabled for this query.")
        return {"messages": info_message,
                "classify": "A",
                "lines": [],
                "headers": []
        }
    
    system_message = SystemMessage(content=f"{CLASSIFIER_PROMPT}")
    full_messages = [system_message] + state["messages"]

    response_messages = classifier_model.invoke(full_messages)
 
    print(f"\n[DEBUG nodes.py classifier_node] classify: {response_messages.classify}")
    return {"classify": response_messages.classify,}

def reflect_node(state: MessageState):
    """LLM evaluates on answer and reflects on whether to re-query or not"""

    print(f"\n[DEBUG nodes.py reflect_node] node invoked")

    system_messages = SystemMessage(content="Look at the messages and check if the last message is final or its now the turn of the user or the ai can not continue (then true), or if the ai is still in planning / executing or got interrupted (then false).")
    full_messages = state["messages"] + [system_messages]

    response_messages = reflect_model.invoke(full_messages)

    return {
        #"final_answer": response_messages.final_answer
        "final_answer": True
    }

# - Tools -

def tool_node(state: MessageState): #this node is currently not in use. use it, when augment orchestrator with tools
    """Performs the tool call"""
    
    print(f"\n[DEBUG nodes.py tool_node] node invoked")

    result = []

    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        args = tool_call["args"].copy() #copy, so that args in main state are not being overwritten

        if tool_call["name"] in ["subagent_tool", "retrieve_logfile_tool"]:
            args["lines"] = state.get("lines", [])
            args["headers"] = state.get("headers", [])

        observation = tool.invoke(args)
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))

    return {"messages": result}

def check_command_node(state: MessageState):
    """checks the query for / commands at the beginning and routes them to the correct strategy
    Aviable commands:
    /set-file {filename}
    /classify {Literal:[A, B, C]}
    /clear-context
    /manual
    Strategies:
    A: retrieval
    B: ingestion
    C: END
    """

    print(f"\n[DEBUG nodes.py check_command_node] node invoked")

    message_content = state["messages"][-1].content

    if isinstance(message_content, list):
        text_parts = [item['text'] for item in message_content if isinstance(item, dict) and item.get('type') == 'text']
        message = "".join(text_parts)
    else:
        message = message_content

    # - No Command -
    if not (re.findall("\A/\w", message)): 
        return {"strategy": "A"}
    
    str = re.findall("\A/\S+\s\S+|\A/\S+", message)
    str = str[0].split()
    command = str[0]
    arg = ""
    if (len(str) > 1):
        arg = str[1]

    # - /set-file -
    if (command == "/set-file"):
        file_path = get_file_path(arg)
        if file_path:
            info_string = f"Starting with Ingestion for {file_path}. \n\nThis may take a while..."
            info_message = AIMessage(content=info_string)
            return {
                "messages": info_message,
                "strategy": "B",
                "file_path": file_path,
                "ingested": False
            }
        else:
            info_message = AIMessage(content="File Path could not be resolved!\nempty file_path")
            return {"messages": info_message, "strategy": "C"}
        
    # - /classify -
    if (command == "/classify"):
        cut_message = re.sub("\A/classify\s\w\s\\n?", "", message)
        new_message = state["messages"][-1].__class__(
            id=state["messages"][-1].id,
            content=cut_message
        )
        return{
            "messages": new_message,
            "strategy": "A",
            "classify": arg,
            "classify_override": True,
        }
    
    # - /clear-context -
    if (command == "/clear-context"):
        info_message = AIMessage(content="Context window has been cleared")
        return {"messages": Overwrite([info_message]), "strategy": "C"}
    
    # - /manual -
    if (command == "/manual"):
        info_message = AIMessage(content=MANUAL)
        return {"messages": info_message, "strategy": "C"}
        
    info_message = AIMessage(content="Command could not be resolved")
    return {"messages": info_message, "strategy": "C"}
    

def ingest_logfile_node(state: MessageState):
    """Loads and prepares the Logfile for ingestion"""

    print(f"\n[DEBUG nodes.py ingest_logfile_node] node invoked")

    print(f"\n[DEBUG nodes.py ingest_logfile_node] ingesting from file: {state['file_path']}")
      
    lines = init_logfile_tool.invoke({"file_path": state["file_path"]})

    headers = ingest_logfile_tool.invoke({"lines": lines})

    info_message = AIMessage(content="Ingestion Completed. Agent is ready for retrieval")

    return {
        "messages": info_message,
        "lines": lines,
        "headers": headers,
    }

def test_retrieve_node(state: MessageState):
    """this node let the LLM scan trough the entire logfile and returns all lines by its relevance to the query"""

    print(f"\n[DEBUG nodes.py test_retrieve_node] node invoked")

    query = state["messages"][-1].content

    context = retrieve_logfile_tool.invoke({"query": query, "lines": state["lines"]})

    return_message = []
    
    return_message.append(HumanMessage(content=f"Retrieved logfile:\n\n{context}"))

    return {"messages": return_message}






# --- Parent Conditional Edges ---

def strategy_edge(state: MessageState) -> Literal["classifier_node", "ingest_logfile_node", END]:
    """Routes, based on which command is called"""

    print(f"\n[DEBUG nodes.py strategy_edge] edge invoked")
    print(f"\n[Debug nodes.py strategy_edge] strategy: {state['strategy']}")

    if state["strategy"] == "A":
        return "classifier_node"
    
    if state["strategy"] == "B":
        return "ingest_logfile_node"

    if state["strategy"] == "C":
        return END
    
    print(f"\n[ERROR nodes.py strategy_edge] Strategy Selection failed. strategy state: {state['strategy']}. Routing to END\n")
    return END


def tool_call_edge(state: MessageState) -> Literal["retrieve_graph", "tool_node", "reflect_node"]:
    """Decide if we should invoke retrieve_graph, perform normal tool call or stop based upon whether the LLM made a tool call"""

    print(f"\n[DEBUG nodes.py tool_call_edge] edge invoked")

    if state["messages"][-1].tool_calls:
        if state["messages"][-1].tool_calls[0]["name"] in ["retrieve_logfile_assistant"]:
            return "retrieve_graph"
        return "tool_node"

    return "reflect_node"

def classify_edge(state: MessageState) -> Literal["test_retrieve_node", "retrieve_graph", "orchestrator_node"]:
    """routing the query based classifier choice"""

    print(f"\n[DEBUG nodes.py classify_edge] edge invoked")

    if state["classify"] == "A":
        return "test_retrieve_node"
    
    if state["classify"] == "B":
        return "retrieve_graph"

    if state["classify"] == "C":
        return "orchestrator_node"

    print(f"\n[ERROR nodes.py classify_edge] Classify Selection failed. classify state: {state['classify']}. Routing to LLM\n")
    return "llm_node"

def retrieve_strategy_edge(state: MessageState) -> Literal["llm_node", "orchestrator_node"]:
    """routing based on classifier choice. this edge is needed for additional complexity, since retrieve_graph is used for B and C"""

    print(f"\n[DEBUG nodes.py retrieve_strategy_edge] edge invoked")
    
    if state["classify"] == "B":
        return "llm_node"

    if state["classify"] == "C":
        return "orchestrator_node"

    print(f"\n[ERROR nodes.py retrieve_edge] Classify Selection failed. classify state: {state['classify']}. Routing to LLM\n")
    return "llm_node"


def reflect_edge(state: MessageState) -> Literal["orchestrator_node", END]:
    """routing based on reflection grade"""# this edge contains logic for MIN_REFLECTION for debugging purposes

    print(f"\n[DEBUG nodes.py reflect_edge] edge invoked")
  
    if state.get("final_answer"):
        return END
    else:
        state["messages"].append(HumanMessage(content="Continue."))
        return "orchestrator_node"



# --- Subgraph Retrieve Nodes ---

def retrieve_start_node(state: RetrieveGraphState):
    """for converting parent graph query into human message"""

    print(f"\n[DEBUG nodes.py retrieve_start_node] node invoked")
    
    result = []
    
    if hasattr(state["messages"][-1], "tool_calls"):
        tool_args = state["messages"][-1].tool_calls[0]["args"]
        query = tool_args.get("query")
        result.append(HumanMessage(content=query))
    else:
        #result.append(HumanMessage(content=state["messages"][-1].content))
        result = state["messages"]

    return {"isolated_context": result}

def retrieve_end_node(state: RetrieveGraphState):
    """for converting final answer into parent graph message"""

    print(f"\n[DEBUG nodes.py retrieve_end_node] node invoked")

    print(f"\n[DEBUG nodes.py retrieve_end_node] subgraph message history:")
    for m in state["isolated_context"]:
        m.pretty_print()

    print(f"\n[DEBUG nodes.py retrieve_end_node] state messages -1 raw: {state['messages'][-1]}")

    result = []

    if hasattr(state["messages"][-1], "tool_calls"):
        result.append(ToolMessage(content=state["isolated_context"][-1].content, tool_call_id=state["messages"][-1].tool_calls[0]["id"]))
    else:
        result.append(AIMessage(content=f"Retrieved context:\n\n{state['isolated_context'][-1].content}\n\nSynthesize answer:"))

    return {"messages": result}


def retrieve_agent_node(state: RetrieveGraphState):
    """LLM performing Retrieval"""

    print(f"\n[DEBUG nodes.py retrieve_agent_node] node invoked")
    
    history = state["isolated_context"]
    has_plan = any("Plan:" in m.content for m in history if hasattr(m, 'content'))
    plan_instruction = "Follow the existing plan." if has_plan else "Create a new plan then proceed.\n PLAN:"

    system_message = SystemMessage(content=f"{RETRIEVER_PROMPT}\n\n{plan_instruction}")
    full_messages = state["isolated_context"] + [system_message]

    response_messages = retrieve_agent_model.invoke(full_messages)
    
    if not isinstance(response_messages, list):
        response_messages = [response_messages]

    return {"isolated_context": response_messages, "retrieve_agent_node": state.get('retrieve_agent_node', 0) +1}

def retrieve_logfile_node(state: RetrieveGraphState):
    """LLM turns query into regex pattern. processes being searched in headers list and then retrieved from lines list and returned as a tool message
    limitations: retrieval max 5000 lines"""

    print(f"\n[DEBUG nodes.py retrieve_logfile_node] node invoked")

    tool_args = state["isolated_context"][-1].tool_calls[0]["args"]
    
    result = []
    
    if (state.get("lines") == [''] or state.get("lines") is None):
        logdata = "[ATTENTION] Either no Logdata ingested yet or Logfile empty. Return this message: Please inform the user immediately to load a Logfile and provide them this instruction: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        result.append(ToolMessage(content=logdata, tool_call_id=state["isolated_context"][-1].tool_calls[0]["id"]))

    else:
        logdata = retrieve_logfile_tool.invoke({
            "query": tool_args.get("query"),
            "lines": state["lines"], 
            "headers": state["headers"]
            })
        
        result.append(ToolMessage(content=logdata, tool_call_id=state["isolated_context"][-1].tool_calls[0]["id"]))

    return {"isolated_context": result}

def retrieve_reflect_node(state: RetrieveGraphState):
    """LLM evaluates on answer and reflects on whether to re-query or not"""

    print(f"\n[DEBUG nodes.py retrieve_reflect_node] node invoked")

    system_messages = SystemMessage(content="Your task is to look at the conversation and check if the ai has answered the user's query. **DO NOT** return false, except the ai got interrupted.")
    full_messages = state["isolated_context"] + [system_messages]

    response_messages = reflect_model.invoke(full_messages)

    return {
        #"final_answer": response_messages.final_answer
        "final_answer": True
    }

# --- Subgraph Retrieve Edges ---

def retrieve_tool_call_edge(state: RetrieveGraphState) -> Literal["retrieve_logfile_node", "retrieve_reflect_node"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    print(f"\n[DEBUG nodes.py retrieve_tool_call_edge] edge invoked")

    if state["isolated_context"][-1].tool_calls:
        return "retrieve_logfile_node"
    
    return "retrieve_reflect_node"

def retrieve_reflect_edge(state: RetrieveGraphState) -> Literal["retrieve_agent_node", "retrieve_end_node"]:
    """routing based on reflection grade"""# this edge contains logic for MIN_REFLECTION for debugging purposes

    print(f"\n[DEBUG nodes.py retrieve_reflect_edge] edge invoked")
  
    if state.get("final_answer"):
        return "retrieve_end_node"
    else:
        state["messages"].append(HumanMessage(content="Continue."))
        return "retrieve_agent_node"