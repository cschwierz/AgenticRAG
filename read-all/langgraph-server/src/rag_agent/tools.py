# Description: Tools, Agents and Models
"""
================================================================================
                           MODUL: tools.py
================================================================================

BESCHREIBUNG:
    Tools und Models für die Nodes.
    Enthält Tool-Definitionen, Modell-Konfigurationen und Funktionen.

TABLE OF CONTENTS:
    1. Imports
    2. Load Config Variables
       - Retrieve
       - Agent
    3. Models
       - LLM Modelle
    4. Tools
       - Subagent Tool
       - Ingest Tool
       - Retrieve Tool
    5. Model & Agent config / Augmentation

AUTOR:           [chris]
DATUM ERSTELLT:  15.05.2026
LETZTES UPDATE:  2024-XX-XX

CHANGELOG:
    v1.0.0 (2024-XX-XX):
        - Initial release

================================================================================
"""

# --- Imports ---

from ast import parse

from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langchain.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage, AnyMessage
import os
import json
import re
from pydantic import BaseModel, Field
from typing import Literal
from rag_agent.logfile_retriever import (
    LogFile,
    parse_logfile,
    search_header,
    retrieve_logfile,
    retrieve_logfile_by_query
)

# --- Config ---

with open("/home/chris/LogfileAnalyzer/read-all/config/config.json", "r") as filejson:
#with open("C:\\Users\\chris\\Desktop\\read-all\\config\\config_win.json", "r") as filejson:
    config = json.load(filejson)

# - subagent -
RETRIEVER_PROMPT_PATH = config["RETRIEVER_PROMPT_PATH"]
with open(RETRIEVER_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    RETRIEVER_PROMPT = filetxt.read()

# - logfile_retriever -
PATTERN_GENERATOR_PROMPT_PATH = config["PATTERN_GENERATOR_PROMPT_PATH"]
with open(PATTERN_GENERATOR_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    PATTERN_GENERATOR_PROMPT = filetxt.read()
FILES_PATH = config["FILES_PATH"]

# - agent -
LLM_MODEL = config["LLM_MODEL"]
FAST_LLM_MODEL = config["FAST_LLM_MODEL"]

# --- Models ---

model = ChatOllama(model=LLM_MODEL, temperature=1, top_k=64, top_p=0.95)
medium_model = ChatOllama(model=LLM_MODEL, reasoning=False, temperature=0, top_k=64, top_p=0.95)
fast_model = ChatOllama(model=FAST_LLM_MODEL, reasoning=False, temperature=0, top_k=20, top_p=0.95)

# --- Tools ---


@tool
def retrieve_logfile_assistant(query: str, lines: list = None, headers: list = None) -> str:
    """
    Invokes the specialized Log Retrieval Agent to execute precise data extraction from logfiles.

    ### INPUT (query)
    Provide a precise subtask formulated in Natural Language or Pseudo Patterns. To ensure high-precision retrieval and avoid context overflow, 
    construct your query using as many as possible of the following Data Schema keys:
    - Temporal: `Start Timestamp`, `End Timestamp` [hh:mm:ss:xxx]
    - Identifiers: `Start Index`, `End Index` [int], `Nummer` [int]
    - Metrics: `Errors` [int], `Warnings` [int]

    *Example Queries*: 
    - "Search for Function: BF_Measure where Errors > 0"
    - "Retrieve processes between 10:25:00 and 11:00:00 with Stopwatch > 300. Return only the Process Headers"
    - "Retrieve all processes with Errors or Warnings between 09:15:00:000 and 09:20:00:000"

    ### OUTPUT
    The tool returns a structured response containing all matching processes. Each match consists of a paired:
    1. **Process Header**: The metadata extracted from the Data Schema.
    2. **Relevant Process Log Lines**: The specific, unadulterated log entries associated with that header.

    ### CONSTRAINT
    Do not use wildcards (*). If the query is too broad, the agent may request further refinement.
    Do not send vague queries. Use the Data schema keys above to narrow the search (e.g., "Search for Nummer: 15400 where Errors > 0").
    If a retrieval reveals a process, you may need to trigger a follow-up task to check the "neighboring process" by querying for the `Index`.

    """

    #This is a Dummy tool, so orchestrator can call the subgraph as a tool
    return "Dummy Tool. if you can read this, something went wrong in the tool call. please inform the human about this finding"
    

@tool
def init_logfile_tool(file_path) -> list:
    """
    Loads and prepares the Logfile for ingestion
    """
    print(f"\n[DEBUG tools.py init_logfile_tool] tool invoked")

    logfile = LogFile(file_path)
    lines = logfile.LINES

    return lines


@tool
def ingest_logfile_tool(lines: list) -> list:
    """
    Parses a headers list of the logfile, which is being used for ingestion
    """
    print(f"\n[DEBUG tools.py ingest_logfile_tool] tool invoked")

    headers = parse_logfile(lines)

    return headers

@tool
def retrieve_logfile_tool(query: str, lines: list = None, headers: list = None) -> str:
    """
    Accesses the current Logfile via a specialized Regex-driven retrieval engine. 
    
    ### ARCHITECTURE
    This tool utilizes an internal **Regex Engineer** component. The process follows this pipeline:
    1. **Input**: You provide a query in Natural Language or Pseudo-Pattern.
    2. **Transformation**: The Regex Engineer transforms your input into a Python `re.search()` compatible regular expression.
    3. **Execution**: The regex is applied to the logfile headers and lines to return matching processes.

    ### CRITICAL WARNING: ENGINE STRICTNESS
    The internal Regex Engineer is **extremely strict** and **error-prone** when encountering malformed or ambiguous queries. 
    - If your query does not follow the schema or logic below, the engine may fail to return results or return an error.
    - **Precision is mandatory.** Do not provide vague instructions.
    - **Context Management**: The tool returns significant amounts of data. You must be highly selective to avoid exceeding the context window.

    ### DATA SCHEMA
    All searches and retrievals must be grounded in the following Data Schema. Use these keys to construct your search patterns:
    - `Start Index: [int]`
    - `End Index: [int]`
    - `Start Timestamp: [hh:mm:ss:xxx]`
    - `End Timestamp: [hh:mm:ss:xxx]`
    - `Nummer: [int]`
    - `Errors: [int]`
    - `Warnings: [int]`

    ### QUERY TRANSFORMATION RULES (To ensure successful Regex generation)
    To guide the tool to a correct query, follow these logic patterns:
    1. **Time Windows**: 
       - If providing a single time (e.g., "14:15"), the engine will automatically create a +/- 5-minute window.
       - If providing a range (e.g., "14:00 to 14:30"), the engine will use the `Start Timestamp` as the primary anchor.
    2. **Error/Warning Thresholds**: 
       - Searching for "all Errors" or "any Warnings" will trigger a "Greater than 0" regex pattern.
    3. **Neighboring Process Lookup**: 
       - To find the **following** process: Use the `End Index` of your current process and add `1` as the new `Start Index`.
       - To find the **previous** process: Use the `Start Index` of your current process and subtract `1` from the `End Index`.

    ### BEST PRACTICES
    - **Multi-Criteria Filtering**: Always combine multiple keys (e.g., Timestamp + Nummer + Errors) to narrow the search space.
    - **Contextual Enrichment**: Include specific values from the schema to increase regex accuracy.
    - **Precision**: Be "severe" with your queries to avoid overwhelming the context window.
    - **Time Windows**: Use a Time Window of a few Minutes. Use ONLY Start Timestamp to search for Time (e.g. Start Timestamp: 14:00 - 14:10)

    ### NEGATIVE CONSTRAINTS (DO NOT)
    - **NO Wildcards**: Never use `*` or `ALL`.
    - **NO Large Windows**: Avoid searching across spans of several hours unless explicitly required.
    - **NO Invalid Keys**: Do not use any search criteria not explicitly listed in the Data Schema.
    - **NO Unnecessary Indexing**: Do not search by `Start Index` or `End Index` unless performing a neighboring process lookup.
    - **NO Unnecessary search criteria**: NEVER search by `End Timestamp` unless explicitly requested by the query

    ### FEW SHOT QUERY EXAMPLES
    - Input (Pseudo): "Start Timestamp BETWEEN 04:25: and 04:30 (in Format hh:mm)"
    - Input (NL): "search for errors between 00:00 and 04:00"
    """

    print(f"\n[DEBUG tools.py retrieve_logfile_tool] tool invoked")

    print(f"\n[DEBUG tools.py retrieve_logfile_tool] query received: {query}")

    buffer = []

    chunk_size = 1000
    chunk_overlap = 50
    n = 0
    m = chunk_size
    len_lines = len(lines)

    for x in range(0, len_lines, chunk_size-chunk_overlap):

        prompt = r"""
**SYSTEM PROMPT**
    
You are a specialized log analysis assistant. 
Your task is to identify and extract the index of every logfile line that is semantically relevant to synthesize the user's query.

Instructions:
1. Carefully analyze each log entry provided.
2. If a line is relevant to the query, include its index in your output.
3. Be severe with the relevance of the line.
4. If no lines are relevant, output an empty list: []
5. Do not include any text, explanations, or metadata in your output. Only return the requested list of index.
6. Be severe with your output. {"index": [...]}

The log entries use the format: {index} {timestamp} {type} : {content}
        """
        # IMPORTANT prompting a structured output in langchain with:
        # gemma4, you must include an example: 6. Be severe with your output. Example: {"index": [123, 345]}
        # qwen and nemotron, you must include a template: 6. Be severe with your output. {"index": [...]}
        # also, be severe with the name of the key, when mentioning it in the Prompt or Format description
        # in this example, literally call it "index" - never "indexes", "indices", whatever

        lines_messages = "\n".join(lines[n:m])

        full_messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=f"<query>\n{query}\n</query>\n\n" + f"<logfile>\n{lines_messages}\n</logfile>\n\n")
        ]

        response_messages = reader_model.invoke(full_messages)

        print(f"\n[DEBUG tools.py retrieve_logfile_tool] q&a for index {n} to {m}:\n\n{full_messages}\n\n{response_messages.index}")

        for ind in response_messages.index:
            if ind not in buffer:
                buffer.append(ind)

        print(f"\n[DEBUG tools.py retrieve_logfile_tool] buffer:{buffer}")

        n = n + chunk_size - chunk_overlap
        m = m + chunk_size - chunk_overlap

        print(f"\n[DEBUG tools.py retrieve_logfile_tool] progress:{100/len_lines*x}%")

    print(f"\n[DEBUG tools.py retrieve_logfile_tool] buffers of relevance: {buffer[:]}")
    tempdata = []
    for buf in buffer[0:]:
        tempdata.append(lines[buf])
    
    logdata = "\n".join(tempdata)

    return logdata


# --- Augment Model with Tools / Agents ---

tools = [retrieve_logfile_assistant]
tools_by_name = {tool.name: tool for tool in tools}


class ClassifierState(BaseModel):
    classify: Literal["A", "B", "C"] = Field(description="Strategy to select.")


classifier_model = fast_model.with_structured_output(ClassifierState)


class ReflectState(BaseModel):
    final_answer: bool = Field(description="is the query answered?")

reflect_model = fast_model.with_structured_output(ReflectState)


class PatternState(BaseModel):
    regex_pattern: str = Field(description="The final, optimized Python regex pattern.")

regex_model = fast_model.with_structured_output(PatternState)


class BufferState(BaseModel):
    index: list[int] = Field(description="A list of unique index representing the index of each relevant log line. index: list[int]")
    
reader_model = fast_model.with_structured_output(BufferState, method="json_mode")



orchestrator_model = model.bind_tools(tools, tool_choice="auto")

retrieve_agent_model = model.bind_tools([retrieve_logfile_tool], tool_choice="auto")

