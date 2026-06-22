# Ingestion and retrieval for Log Files
# it contains only deterministic parse functions, no llm embeddings
"""
================================================================================
                           MODUL: logfile_retriever.py
================================================================================

BESCHREIBUNG:
    Ingestion von Header (der Prozesse) aus Logfiles und Suche in Headern mit RegEx mit Retrieval aus der Logfile

TABLE OF CONTENTS:
    1. Imports
    2. Load Config Variables
    3. Parse
        Ingestion into a Headers List
    4. Search
        With RegEx Pattern in Headers List - returns matching Headers
    5. Retrieve
        Generate a string with matching Headers and its Processes

AUTOR:           [chris]
DATUM ERSTELLT:  29.05.2026
LETZTES UPDATE:  2024-XX-XX

CHANGELOG:
    v1.0.0 (2024-XX-XX):
        - Initial release

================================================================================
"""

# --- Imports ---

import os
import json
import re
from langchain_community.document_loaders import TextLoader
from pathlib import Path

# --- Config ---

with open("/home/chris/LogfileAnalyzer/config/config.json", "r") as filejson:
#with open("C:\\Users\\chris\\Documents\\Workspace\\LogfileAnalyzer\\config\\config_win.json", "r") as filejson:
    config = json.load(filejson)

FILES_PATH = config["FILES_PATH"]
MAX_RETRIEVAL = config["MAX_RETRIEVAL"]

# --- File ---


class LogFile:
    """
    Loads and provides the Logfile as a List of lines
    Parameter: Absolute Path of the Log File
    """

    def __init__(self, file_path):

        if file_path is None:
            print(f"\n[ERROR logfile_retriever_pipeline.py LogFile] no parameter passed to the class.")

        self.loader = TextLoader(file_path, encoding="latin-1")
        self.file = self.loader.load()

        self.FILE = self.file[0].page_content

        self.LINES = self.FILE.split("\n")
        print(f"\n[DEBUG logfile_retriever_pipeline LogFile] created {len(self.LINES)} lines for {file_path}")

# --- File Path

def get_file_path(file_name: str) -> str:
    """
    Function to search for a file name locally and return its absolute filepath.
    """

    print(f"\n[DEBUG logfile_retriever_pipeline.py get_file_path] function called.")
    print(f"\n[DEBUG logfile_retriever_pipeline.py get_file_path] file_name: {file_name}")
    
    # Default search paths
    
    search_paths = [
        os.getcwd(),
        os.path.join(os.getcwd(), "config"),
        os.path.join(os.getcwd(), "logs"),
        os.path.join(os.getcwd(), "data"),
        FILES_PATH
    ]
    
    # Create Path objects for efficient searching
    search_dirs = [Path(p) for p in search_paths]
    
    # Search for the file
    for search_dir in search_dirs:
        try:
            # Try exact match first
            file_path = search_dir / file_name
            if file_path.exists():
                return str(file_path.resolve())
            
            # Try case-insensitive search
            for file in search_dir.rglob(file_name):
                if file.is_file():
                    return str(file.resolve())
            
            # Try partial match (file_name as substring)
            for file in search_dir.rglob("*"):
                if file.is_file() and file_name.lower() in file.name.lower():
                    return str(file.resolve())
                    
        except (PermissionError, OSError):
            # Skip directories we can't access
            continue
    
    return None

# --- Parse ---


def parse_logfile(lines: list) -> list:
    """
    Takes a Logfile LINES and generates a headers list of the processes in that Logfile
    Parameter: LogFile.LINES - Returns: list with headers
    Struktur:
        Start Index: int
        End Index: int
        Start Timestamp: hh:mm:ss
        End Timestamp: hh:mm:ss
        Nummer: nnnnnnn
        ERRORS: int
        WARNINGS: int
    """
    headers = []

    start_index = 0
    end_index = 0
    error_counter = 0
    warning_counter = 0
    len_lines = len(lines) - 1

    while end_index < len_lines:

        for i, line in enumerate(lines[start_index:]):
            match = re.search("Process Start", line)

            if match:
                end_index = i + start_index
                break

        if (end_index == start_index):
            end_index = len_lines

        for i, line in enumerate(lines[start_index:end_index]):
            match = re.search("Nummer", line)

            if match:
                parse = line[match.start() :]
                parse = re.search("\d+", parse)
                nummer = parse[0]
                break

        for i, line in enumerate(lines[start_index:end_index]):
            match = re.search(" ERROR", line)

            if match:
                error_counter = error_counter + 1

        for i, line in enumerate(lines[start_index:end_index]):
            match = re.search(" WARNING", line)

            if match:
                warning_counter = warning_counter + 1

        start_timestamp = lines[start_index][:12]
        end_timestamp = lines[end_index][:12]

        headers.append(f"""
Start Index:        {start_index}
End Index:          {end_index}
Start Timestamp:    {start_timestamp}
End Timestamp:      {end_timestamp}
Nummer:             {nummer}
Errors:             {error_counter}
Warnings:           {warning_counter}
            """)

        # set variables for next loop
        if end_index == len_lines:
            break
        end_index = end_index + 1
        start_index = end_index
        error_counter = 0
        warning_counter = 0

    print(f"\n[DEBUG logfile_retriever_pipeline.py parse_logfile] {len(headers)} headers generated")
    return headers


# --- Search ---


def search_header(headers: list, pattern: str) -> list:
    """
    Takes a Headers List and a RegEx pattern and performs a search.
    Parameter: headers[]; pattern str - Returns: list with search matches
    Syntax for Pattern:,
    Todo implement multiple criterias for one pattern - see re docs
    """
    matches = []

    for i, header in enumerate(headers):
        match = re.search(pattern, header, re.DOTALL)

        if match:
            matches.append(header)

    print(f"\n[DEBUG logfile_retriever_pipeline.py search_header] found: {len(matches)} processes")

    return matches


# --- Retrieve ---


def retrieve_logfile(matches: list, lines: list) -> str:
    """
    takes a Headers list and returns a string with logdata from the processes associated with the header
    returns a error, if the logdata exceeds over 5000 lines
    """

    # counting all lines
    total_lines = 0
    processes = []

    for i, match in enumerate(matches):
        start_line = re.search("Start Index:", match)
        end_line = re.search("End Index:", match)

        if start_line:
            parse = match[start_line.start() :]
            parse = re.search("\d+", parse)
            start_index = int(parse[0])

        if end_line:
            parse = match[end_line.start() :]
            parse = re.search("\d+", parse)
            end_index = int(parse[0])

        process_lines = end_index - start_index

        total_lines = total_lines + process_lines

        processes.append(f"\n\nProcess header:\n{match}\nProcess log:")
        processes.append("\n".join(lines[start_index:end_index]))

    if total_lines > MAX_RETRIEVAL:
        return f"[ATTENTION] retrieved {total_lines} lines of Logdata. Logdata is limited to {MAX_RETRIEVAL} lines due to context window. please use this tool again and apply a more strict search query."
    # todo: in this case go back to pattern generator llm and repeat
    if total_lines == 0:
        return f"[ATTENTION] retrieved 0 lines of Logdata"

    print(f"\n[DEBUG logfile_retriever_pipeline.py retrieve_logfile] retrieved: {total_lines} lines of Logdata")

    logdata = "\n\nProcess:\n".join(processes)

    return logdata
