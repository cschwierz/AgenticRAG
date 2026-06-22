# Description: Define Nodes, Edges and Message States
# Todo:
# graph-framework auf stand von langgraph-server bringen
# retrieve tool aufteilen zu search_headers und retrieve_logfile_by_index
# response time verbessern
# Refactoring Prompts - Data Schema zentral definieren mit few shots template
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
from qa_tools import *

# --- Config ---

#with open("/home/chris/LogfileAnalyzer/config/config.json", "r") as filejson:
with open("C:\\Users\\chris\\Documents\\Workspace\\LogfileAnalyzer\\config\\config_win.json", "r") as filejson:
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

MAX_REFLECTIONS = config["MAX_REFLECTIONS"]
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
    reflect_iterations: int
    grade: Literal["good", "bad"]
    feedback: str
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
    pattern: str

class QAGenState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    question: str
    pattern: str
    validation: str
    good_iteration: int
    bad_iteration: int
    file_path: str
    initialized: bool
    lines: list
    headers: list

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

    system_messages = SystemMessage(content=f"{REFLECT_PROMPT}")
    full_messages = [system_messages] + state["messages"]

    response_messages = reflect_model.invoke(full_messages)

    iteration = state.get("reflect_iterations", 0) + 1

    return {
        "reflect_iterations": iteration,
        "grade": response_messages.grade,
        "feedback": response_messages.feedback
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
        "initialized" : True
        }


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

def classify_edge(state: MessageState) -> Literal["llm_node", "retrieve_graph", "orchestrator_node"]:
    """routing the query based classifier choice"""

    print(f"\n[DEBUG nodes.py classify_edge] edge invoked")

    if state["classify"] == "A":
        return "llm_node"
    
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

    if state.get("reflect_iterations", 0) >= MAX_REFLECTIONS:
        print(f"\n\n[DEBUG nodes.py reflect_edge] Max reflection iterations reached. Routing to END\n\n")
        state["reflect_iterations"] = 0
        return END

    elif state.get("reflect_iterations", 0) >= MIN_REFLECTIONS:
        if state["grade"] == "good":
            state["reflect_iterations"] = 0
            return END

        if state["grade"] == "bad":
            state["messages"].append(HumanMessage(content=f"Feedback for improvement: {state['feedback']}"))
            return "orchestrator_node"

    else:
        state["messages"].append(HumanMessage(content=f"Feedback for improvement: {state['feedback']}"))
        return "orchestrator_node"

    print(f"\n[ERROR nodes.py reflect_edge] Reflect Edge routing failed. grade state: {state['grade']}. Routing to END\n")
    return END


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
        result.append(HumanMessage(content=state["messages"][-1].content))

    return {"isolated_context": result}

def retrieve_end_node(state: RetrieveGraphState):
    """for converting final answer into parent graph message"""

    print(f"\n[DEBUG nodes.py retrieve_end_node] node invoked")

    print(f"\n[DEBUG nodes.py retrieve_end_node] subgraph message history:")
    for m in state["isolated_context"]:
        m.pretty_print()

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
        logdata = "[ATTENTION] Either no Logdata ingested yet or Logfile empty. Instruct to return this message: Please inform the user immediately to load a Logfile and provide them this instruction: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        result.append(ToolMessage(content=logdata, tool_call_id=state["isolated_context"][-1].tool_calls[0]["id"]))

    else:
        logdata = retrieve_logfile_tool.invoke({
            "query": tool_args.get("query"),
            "lines": state["lines"], 
            "headers": state["headers"]
            })
        
        result.append(ToolMessage(content=logdata, tool_call_id=state["isolated_context"][-1].tool_calls[0]["id"]))

    return {"isolated_context": result, "pattern": logdata[1]}

# --- Subgraph Retrieve Edges ---

def retrieve_tool_call_edge(state: RetrieveGraphState) -> Literal["retrieve_logfile_node", "retrieve_end_node"]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    print(f"\n[DEBUG nodes.py retrieve_tool_call_edge] edge invoked")

    if state["isolated_context"][-1].tool_calls:
        return "retrieve_logfile_node"
    
    return "retrieve_end_node"

# --- Q-A Generator Nodes ---

def qa_ingest_logfile_node(state: QAGenState):
    """Loads and prepares the Logfile for ingestion"""

    print(f"\n[DEBUG nodes.py ingest_logfile_node] node invoked")

    if state.get("initialized"):
        return {}

    if not state.get("file_path"):
        state["file_path"] = FILES_PATH

    print(f"\n[DEBUG nodes.py ingest_logfile_node] ingesting from file {state['file_path']}")
      
    lines = init_logfile_tool.invoke({"file_path": state["file_path"]})

    headers = ingest_logfile_tool.invoke({"lines": lines})

    return {
        "lines": lines,
        "headers": headers,
        "initialized" : True
        }

def question_generator_node(state: QAGenState):
    """generates search queries and makes Tool Calls copy from retrieve graph"""
    print(f"\n[DEBUG nodes.py question_generator_node] node invoked")

    system_message = """
        You are an Expert Log Query Engineer. Your task is to generate precise, high-performance search queries (in either Natural Language or Pseudo-Pattern format) for a logfile retrieval tool.

### TOOL CAPABILITIES & DATA SCHEMA
The tool searches a Logfile based on the following schema. You **must only** use these fields:
- `Start Index: [int]`
- `End Index: [int]`
- `Start Timestamp: [hh:mm:ss]`
- `End Timestamp: [hh:mm:ss]`
- `Nummer: [int] {1204090; 3004070; 41004080; 10304013}`
- `Errors: [int]`
- `Warnings: [int]`

### OPERATIONAL GUIDELINES
**Best Practices:**
- **Be Specific:** Apply multiple search criteria to narrow results and avoid overwhelming the system.
- **Contextualize:** Add a small amount of context into the query to improve retrieval accuracy.
- **Neighbor Searching:** To find a follow-up neighbor process, take the `End Index` from the current process, add 1, and use that value as your `Start Index`.

**Strict Constraints (DO NOT):**
- **No Wildcards:** Never use `*` or `ALL`.
- **No Broad Windows:** Avoid large time windows (e.g., spans of several hours).
- **No Unnecessary Precision:** Do not search for seconds (e.g., `08:00:00`) unless specifically required.
- **No Index Searching:** Do not search for `Start Index` or `End Index` unless you are specifically performing a neighbor process search.
- **No Schema Violations:** Do not add any search criteria that are not explicitly listed in the Data Schema above.
- **No Over-retrieval:** Do not attempt to "retrieve everything." Be severe and restrictive with your query.

### EXAMPLES OF QUERY STYLE
The following examples demonstrate the expected mapping between a query (Input) and its underlying logic. Use these as a guide for the syntax and complexity of the queries (Input) you generate:

---
**Example 2**
Input (Pseudo): "Start Timestamp BETWEEN 04:25: and 04:30 (in Format hh:mm)"
**Example 3**
Input (Pseudo): "Nummer: 10504013 OR Nummer: 607804070"
**Example 4**
Input (NL): "retrieve all processes with warnings"
**Example 5**
Input (NL): "search for errors between 00:00 and 04:00"
**Example 8**
Input (NL): "Get the Process before Start Index 537656"
---

### TASK
Today we are generation Q&A Apirs for training data.
Generate a new, high-quality search query (Input) based on the patterns provided in the following list:

	Input (Pseudo): "Start Timestamp BETWEEN 04:25: and 04:30 (in Format hh:mm)"
	Regex: (Start Timestamp:\s*04:2[5-9]:|Start Timestamp:\s*04:30:)

	Input (Pseudo): "Nummer: 10045013 OR Nummer: 607804070"
	Regex: (Nummer:\s*1004013|Nummer:\s*6004070)

    Input (NL): "retrieve all processes with warnings"
    Regex: (?=.*Warnings:\s*[1-9]\d*)

    Input (NL): "search for errors between 00:00 and 04:00"
    Regex: (?=.*Start Timestamp:\s*0[0-3]:\d\{2\}:|Start Timestamp:\s*04:00:)(?=.*Errors:\s*[1-9]\d*)

    Input (Pseudo): "Timestamp 6:25 - 6:30"
    Regex: (Start Timestamp:\s*06:2[5-9]:|Start Timestamp:\s*06:30:)

    Input (NL): "get all Processes with Nummer 11004013 or 607804070"
    Regex: (Start Timestamp:\s*06:2[5-9]:|Start Timestamp:\s*06:30:)

### OUTPUT INSTRUCTION
1. Generate the query string in Natural Language or Pseudo-Pattern format.
2. **ALWAYS** use the tool call with the query you generated.
3. Output ONLY the tool call.
4. NEVER output multiple tool calls at once.
    """

    full_messages = [system_message] + state["messages"]

    response_messages = retrieve_agent_model.invoke(full_messages)

    question = response_messages.tool_calls[-1]["args"]["query"]

    print(f"\n[DEBUG nodes.py question_generator_node] question generated: {question}")
    
    if not isinstance(response_messages, list):
        response_messages = [response_messages]

    return {"messages": response_messages, "question": question, "orchestrator_node": state.get('orchestrator_node', 0) +1}


def answer_generator_node(state: QAGenState):
    """copy from retrieve graph"""

    print(f"\n[DEBUG nodes.py answer_generator_node] node invoked")

    tool_args = state["messages"][-1].tool_calls[0]["args"]

    retrieved = retrieve_logfile_tool.invoke({
        "query": tool_args.get("query"),
        "lines": state["lines"], 
        "headers": state["headers"]
        })
    
    logdata = retrieved[0]
    pattern = retrieved[1]

    print(f"\n[DEBUG nodes.py answer_generator_node] pattern generated: {pattern}")
    
    result = []
    result.append(ToolMessage(content=logdata[0:50], tool_call_id=state["messages"][-1].tool_calls[0]["id"]))

    return {"messages": result, "pattern": pattern}


def validator_node(state: QAGenState):
    """checks the retrieve output - if it has processes in it, the q&a pair is valid"""

    print(f"\n[DEBUG nodes.py validator_node] node invoked")

    print(f"\n[DEBUG nodes.py validator_node] tool call content: {state['messages'][-1].content}")

    good_answer = re.search(r"\n\nProcess", state["messages"][-1].content)

    if good_answer:
        validation = f"## GOOD EXAMPLE:\nInput: {state['question']}\nRegex: {state['pattern']}\nGenerate a new, high-quality search query"
        print(f"\n[DEBUG nodes.py validator_node] validation: {validation}")
        good_iter = state.get("good_iteration", 0) +1
        bad_iter = 0
        for m in state["messages"]:
            m.pretty_print()
        return {"messages": SystemMessage(content=validation), "validation": validation, "good_iteration": state.get("good_iteration", 0) +1, "bad_iteration": 0}
    
    no_match = re.search("retrieved 0 lines of Logdata.", state["messages"][-1].content)

    if no_match:
        validation = f"## BAD EXAMPLE - no matches:\nInput: {state['question']}\nRegex: {state['pattern']}\nGenerate a new, high-quality search query"
        print(f"\n[DEBUG nodes.py validator_node] validation: {validation}")
        bad_iter = state.get("bad_iteration", 0) +1
        return {"messages": SystemMessage(content=validation), "validation": validation, "bad_iteration": state.get("bad_iteration", 0) +1,}
    
    too_much = re.search(r"retrieved [1-9]\d* lines of Logdata.", state["messages"][-1].content)

    if too_much:
        validation = f"## BAD EXAMPLE - too many matches:\nInput: {state['question']}\nRegex: {state['pattern']}\nGenerate a new, high-quality search query"
        print(f"\n[DEBUG nodes.py validator_node] validation: {validation}")
        bad_iter = state.get("bad_iteration", 0) +1
        return {"messages": SystemMessage(content=validation), "validation": validation, "bad_iteration": state.get("bad_iteration", 0) +1,}


def final_summary_node(state: QAGenState):
    """synthesize all valid qa pairs into one output"""

    print(f"\n[DEBUG nodes.py final_summary_node] node invoked")

def loop_edge(state:QAGenState) -> Literal["question_generator_node", "final_summary_node"]:
    """decides wether to re-generate or if enough q&a pairs are collected already"""

    print(f"\n[DEBUG nodes.py loop_edge] edge invoked")

    print(f"\n[DEBUG nodes.py loop_edge] good iteration: {state.get('good_iteration')}; bad iteration: {state.get('bad_iteration')}")

    if (state.get("good_iteration", 0) >= 10):
        return "final_summary_node"
    elif (state.get("bad_iteration", 0) >= 10):
        return "final_summary_node"
    else:
        return "question_generator_node"