# Description: Tools, Agents and Models
"""
================================================================================
                           MODUL: tools.py
================================================================================

BESCHREIBUNG:
    Tools, Agents und Models für die Nodes.
    Enthält Tool-Definitionen, Modell-Konfigurationen und Agent-Setups.

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
from langchain_core.prompts import PromptTemplate
import os
import json
from pydantic import BaseModel, Field
from typing import Literal
from logfile_retriever import (
    LogFile,
    parse_logfile,
    search_header,
    retrieve_logfile,
)

# --- Config ---

with open("/home/chris/LogfileAnalyzer/config/config.json", "r") as filejson:
#with open("C:\\Users\\chris\\Documents\\Workspace\\LogfileAnalyzer\\config\\config_win.json", "r") as filejson:
    config = json.load(filejson)

# - subagent -
RETRIEVER_PROMPT_PATH = config["RETRIEVER_PROMPT_PATH"]
with open(RETRIEVER_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    RETRIEVER_PROMPT = filetxt.read()

# - logfile_retriever -
PATTERN_GENERATOR_PROMPT_PATH = config["PATTERN_GENERATOR_PROMPT_PATH"]
with open(PATTERN_GENERATOR_PROMPT_PATH, "r", encoding="utf-8") as filetxt:
    PATTERN_GENERATOR_PROMPT = filetxt.read()
DOCUMENT_PATH = config["DOCUMENT_PATH"]

# - agent -
LLM_MODEL = config["LLM_MODEL"]

# --- Models ---

model = ChatOllama(model=LLM_MODEL, temperature=0)
fast_model = ChatOllama(model=LLM_MODEL, reasoning=False, temperature=0)

# --- Tools ---


@tool
def retrieve_logfile_assistant(query: str, lines: list = None, headers: list = None) -> str:
    """
    Use this assistant for context gathering from the current Logfiles. Give it a Subtask with context as query.
    It will return one or multiple Processes in the following format:
    # Process Header:
    - `Start Index: [int]`
    - `End Index: [int]`
    - `Start Timestamp: [hh:mm:ss]`
    - `End Timestamp: [hh:mm:ss]`
    - `Nummer: [int]`
    - `Errors: [int]`
    - `Warnings: [int]`
    # Process log:
    *summarized lines of log data*
    It is reccommended to specifically search for keys in the process header.
    """
    #This is a Dummy tool, so orchestrator can call the subgraph as a tool
    return "Dummy Tool. if you can read this, something went wrong in the tool call. please inform the human about this finding"
    

@tool
def init_logfile_tool(document_path=None) -> list:
    """
    Loads and prepares the Logfile for ingestion
    ToDo: human in the Loop, to confirm the document path
    """
    print(f"\n[DEBUG tools.py init_logfile_tool] tool invoked")

    if document_path is None:
        document_path = DOCUMENT_PATH
    else:
        DOCUMENT_PATH = document_path

    logfile = LogFile(document_path)
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
def retrieve_logfile_tool(query: str, lines: list = None, headers: list = None) -> list:
    """
    This tool has access to the current Logfile. Use this as a search tool to retrieve process logs from the Logfile.
    It takes a retrieve query in Natural Language or Pseudo Pattern with some context.
    This tool works by generating search patterns and applying them to a logfile and returning processes with matching search patterns.
    use the following Data schema for search criteria.
    Data Schema:
    - `Start Index: [int]`
    - `End Index: [int]`
    - `Start Timestamp: [hh:mm:ss]`
    - `End Timestamp: [hh:mm:ss]`
    - `Nummer: [int]`
    - `Errors: [int]`
    - `Warnings: [int]`
    Example queries:
    - Search between 15:00 and 16:00 for Nummer more than 300000 or Warnings between 1 and 5
    - Start Index 13:00 - 13:20 and Nummer 10304042
    Best practice:
    - apply many search criteria
    - this tool may easily return too much context, so be severe with your query
    - add a little bit of context into the query
    - in order to get the followup neighbour process, take End index from the current process, add 1 and search with that number as start index
    Dont do this:
    - retrieve everything
    - * / ALL
    - Big Time Windows (over several hours)
    - search for seconds, when they are not required: 08:00:00 and 08:10:00
    - Dont search for Start Index, End Index, unless you need the neighbour Process
    - Do not add searxh criteria thats not listed in Data Schema.
    """

    print(f"\n[DEBUG tools.py retrieve_logfile_tool] tool invoked")

    full_messages = PATTERN_GENERATOR_PROMPT + f"Go Ahead!\nInput: {query}\nRegex:"

    pattern = regex_model.invoke(full_messages)

    print(f"\n[DEBUG tools.py retrieve_logfile_tool] pattern generated: {pattern.regex_pattern}")

    matches = search_header(headers, pattern.regex_pattern)

    logdata = retrieve_logfile(matches, lines)

    return [logdata, pattern] #return list bc i need pattern for Debug in q-a_generator.py


# --- Augment Model with Tools / Agents ---

tools = [retrieve_logfile_assistant]
tools_by_name = {tool.name: tool for tool in tools}


class ClassifierState(BaseModel):
    strategy: Literal["A", "B", "C"] = Field(description="Strategy to select")

classifier_model = fast_model.with_structured_output(ClassifierState)


class ReflectState(BaseModel):
    # reflect_iterations: int = Field(description="Number of reflection iterations performed") #remove this bc the llm should not write this
    grade: Literal["good", "bad"] = Field(description="Grade of the answer quality")
    feedback: str = Field(
        description="Reflection on the answer quality. feedback and criteria"
    )

reflect_model = model.with_structured_output(ReflectState)


class PatternState(BaseModel):
    regex_pattern: str = Field(description="The final, optimized Python regex pattern.")

regex_model = fast_model.with_structured_output(PatternState)


orchestrator_model = model.bind_tools(tools, tool_choice="auto")

retrieve_agent_model = model.bind_tools([retrieve_logfile_tool], tool_choice="auto")

