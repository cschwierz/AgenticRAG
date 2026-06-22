# Description: Graph workflow
"""
================================================================================
                           MODUL: graph.py
================================================================================

BESCHREIBUNG:
    Definiert den Graph & verbindet die Nodes

TABLE OF CONTENTS:
    1. Imports
    2. Load Config Variables
    3. Graphs
    4. Invoke

AUTOR:           [chris]
DATUM ERSTELLT:  15.05.2026
LETZTES UPDATE:  2024-XX-XX

CHANGELOG:
    v1.0.0 (2024-XX-XX):
        - Initial release

================================================================================
"""

# --- Imports ---

from langgraph.graph import StateGraph, START, END
from langchain.messages import HumanMessage
from nodes import *
import os
import json

# --- Configs ---

#with open("/home/chris/LogfileAnalyzer/config/config.json", "r") as filejson:
with open("C:\\Users\\chris\\Documents\\Workspace\\LogfileAnalyzer\\config\\config_win.json", "r") as filejson:
    config = json.load(filejson)

QUERY_SAMPLE = config["QUERY_SAMPLE"]

# --- Graphs ---

retrieve_graph_builder = StateGraph(RetrieveGraphState)

retrieve_graph_builder.add_node("retrieve_start_node", retrieve_start_node)
retrieve_graph_builder.add_node("retrieve_end_node", retrieve_end_node)
retrieve_graph_builder.add_node("retrieve_agent_node", retrieve_agent_node)
retrieve_graph_builder.add_node("retrieve_logfile_node", retrieve_logfile_node)

retrieve_graph_builder.add_edge(START, "retrieve_start_node")
retrieve_graph_builder.add_edge("retrieve_start_node", "retrieve_agent_node")
retrieve_graph_builder.add_conditional_edges("retrieve_agent_node", retrieve_tool_call_edge, ["retrieve_logfile_node", "retrieve_end_node"])
retrieve_graph_builder.add_edge("retrieve_logfile_node", "retrieve_agent_node")
retrieve_graph_builder.add_edge("retrieve_end_node", END)

retrieve_graph = retrieve_graph_builder.compile()


graph_builder = StateGraph(MessageState)

graph_builder.add_node("check_command_node", check_command_node)
graph_builder.add_node("ingest_logfile_node", ingest_logfile_node)
graph_builder.add_node("llm_node", llm_node)
graph_builder.add_node("orchestrator_node", orchestrator_node)
graph_builder.add_node("classifier_node", classifier_node)
graph_builder.add_node("tool_node", tool_node)
graph_builder.add_node("retrieve_graph", retrieve_graph)
graph_builder.add_node("reflect_node", reflect_node)

graph_builder.add_edge(START, "check_command_node")
graph_builder.add_conditional_edges("check_command_node", strategy_edge, ["classifier_node", "ingest_logfile_node", END])
graph_builder.add_edge("ingest_logfile_node", END)
graph_builder.add_conditional_edges("classifier_node",classify_edge,["llm_node", "retrieve_graph", "orchestrator_node"],)
graph_builder.add_edge("llm_node", END)
graph_builder.add_conditional_edges("orchestrator_node", tool_call_edge, ["retrieve_graph", "tool_node", "reflect_node"])
graph_builder.add_edge("tool_node", "orchestrator_node")
graph_builder.add_conditional_edges("retrieve_graph", retrieve_strategy_edge, ["llm_node", "orchestrator_node"])
graph_builder.add_conditional_edges("reflect_node", reflect_edge, ["orchestrator_node", END])

graph = graph_builder.compile()

print(graph.get_graph().draw_mermaid())
print(graph.get_graph().draw_ascii())

# --- Invoke ---
messages = [HumanMessage(content=f"{QUERY_SAMPLE}")]
messages = graph.invoke({"messages": messages})
for m in messages["messages"]:
    m.pretty_print()
