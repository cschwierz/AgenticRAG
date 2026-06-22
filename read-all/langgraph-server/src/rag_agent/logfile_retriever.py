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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# --- Config ---

with open("/home/chris/LogfileAnalyzer/read-all/config/config.json", "r") as filejson:
#with open("C:\\Users\\chris\\Desktop\\read-all\\config\\config_win.json", "r") as filejson:
    config = json.load(filejson)

FILES_PATH = config["FILES_PATH"]
MAX_RETRIEVAL = config["MAX_RETRIEVAL"]
DEFAULT_CONTEXT_LINES = 2
DEFAULT_LIMIT = 30

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

        raw_lines = self.FILE.split("\n")
        
        self.LINES = [f"{idx} {line}" for idx, line in enumerate(raw_lines, start=0)]

        print(f"\n[DEBUG logfile_retriever_pipeline LogFile] created {len(self.LINES)} lines for {file_path}")

@dataclass
class ProcessRecord:
    start_index: int
    end_index: int
    start_timestamp: str = ""
    end_timestamp: str = ""
    nummer: str = ""
    errors: int = 0
    warnings: int = 0

    def to_header(self) -> str:
        stopwatch = "" if self.stopwatch is None else str(self.stopwatch)
        return (
            f"Start Index:        {self.start_index}\n"
            f"End Index:          {self.end_index}\n"
            f"Start Timestamp:    {self.start_timestamp}\n"
            f"End Timestamp:      {self.end_timestamp}\n"
            f"Nummer:             {self.nummer}\n"
            f"Errors:             {self.errors}\n"
            f"Warnings:           {self.warnings}"
        )

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


def _first_regex(lines: List[str], pattern: str, default: str = "") -> str:
    rx = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        m = rx.search(line)
        if m:
            return m.group(1).strip() if m.groups() else m.group(0).strip()
    return default


def _timestamp(line: str) -> str:
    m = re.match(r"\s*(\d{1,2}:\d{2}:\d{2}(?::\d{1,3})?)", line or "")
    return m.group(1) if m else (line[:12].strip() if line else "")


def _parse_stopwatch(lines: List[str]) -> Optional[int]:
    for line in lines:
        if "STOPWATCH" in line.upper():
            nums = re.findall(r"\d+", line)
            if nums:
                return int(nums[-1])
    return None


def _segment_boundaries(lines: List[str]) -> List[Tuple[int, int]]:
    boundaries: List[Tuple[int, int]] = []
    start = 0
    for i, line in enumerate(lines):
        if i > start and "  Protocol_Start" in line:
            boundaries.append((start, i))
            start = i + 1
    if start < len(lines) - 1:
        boundaries.append((start, len(lines) - 1))
    return boundaries


def parse_records(lines: List[str]) -> List[ProcessRecord]:
    records: List[ProcessRecord] = []
    for start, end in _segment_boundaries(lines):
        chunk = lines[start:end]
        if not chunk:
            continue
        rec = ProcessRecord(
            start_index=start,
            end_index=end,
            start_timestamp=_timestamp(lines[start]) if start < len(lines) else "",
            end_timestamp=_timestamp(lines[end]) if end < len(lines) else "",
            nummer=_first_regex(chunk, r"Nummer\D+(\d+)", ""),
            errors=sum(1 for l in chunk if " ERROR" in l.upper()),
            warnings=sum(1 for l in chunk if " WARNING" in l.upper()),
        )
        records.append(rec)
    print(f"[DEBUG parse_records] generated {len(records)} process records")
    return records


def parse_logfile(lines: List[str]) -> List[str]:
    """Backward-compatible API: returns headers as strings."""
    return [r.to_header() for r in parse_records(lines)]


# --- Search ---



def _header_to_record(header: str) -> ProcessRecord:
    def val(key: str) -> str:
        m = re.search(rf"{re.escape(key)}\s*(.*)", header)
        return m.group(1).strip() if m else ""

    def intval(text: str) -> Optional[int]:
        nums = re.findall(r"\d+", text or "")
        return int(nums[0]) if nums else None

    return ProcessRecord(
        start_index=intval(val("Start Index:")) or 0,
        end_index=intval(val("End Index:")) or 0,
        start_timestamp=val("Start Timestamp:"),
        end_timestamp=val("End Timestamp:"),
        nummer=val("Nummer:"),
        errors=intval(val("Errors:")) or 0,
        warnings=intval(val("Warnings:")) or 0,
    )


def _time_to_ms(t: str) -> Optional[int]:
    if not t:
        return None
    m = re.search(r"(\d{1,2}):(\d{2})(?::(\d{2}))?(?::(\d{1,3}))?", t)
    if not m:
        return None
    h, mi, s, ms = m.groups()
    return ((int(h) * 60 + int(mi)) * 60 + int(s or 0)) * 1000 + int((ms or "0").ljust(3, "0")[:3])


def parse_query(query: str) -> Dict[str, Any]:
    """Small deterministic query parser for common log-analysis questions."""
    q = query or ""
    ql = q.lower()
    spec: Dict[str, Any] = {
        "nummer": None,
        "errors_gt": None,
        "warnings_gt": None,
        "start_after": None,
        "start_before": None,
        "limit": DEFAULT_LIMIT,
        "return_mode": "compact",  # compact | headers | full
        "context_lines": DEFAULT_CONTEXT_LINES,
    }

    for key in ["nummer"]:
        m = re.search(rf"{key}\.?\s*[:=]?\s*(\d+)", q, re.I)
        if m:
            spec[key] = m.group(1)

    if re.search(r"\berror(s)?\b|\bfehler\b", ql):
        spec["errors_gt"] = 0
    if re.search(r"\bwarning(s)?\b|\bwarnung", ql):
        spec["warnings_gt"] = 0

    times = re.findall(r"\b\d{1,2}:\d{2}(?::\d{2})?(?::\d{1,3})?\b", q)
    if len(times) >= 2:
        spec["start_after"] = times[0]
        spec["start_before"] = times[1]
    elif len(times) == 1:
        center = _time_to_ms(times[0])
        if center is not None:
            # +/- 5 minutes. Store as ms directly.
            spec["start_after_ms"] = max(0, center - 5 * 60 * 1000)
            spec["start_before_ms"] = center + 5 * 60 * 1000

    m = re.search(r"\blimit\s*[:=]?\s*(\d+)\b", q, re.I)
    if m:
        spec["limit"] = max(1, min(int(m.group(1)), 200))

    if re.search(r"\b(full|complete|raw)\b", ql):
        spec["return_mode"] = "full"
    elif re.search(r"\b(headers? only|summary only|only headers?)\b", ql):
        spec["return_mode"] = "headers"

    return spec



# --- Retrieve ---




def _matches(rec: ProcessRecord, spec: Dict[str, Any]) -> bool:
    if spec.get("nummer") and spec["nummer"] not in rec.nummer:
        return False
    if spec.get("errors_gt") is not None and not (rec.errors > spec["errors_gt"]):
        return False
    if spec.get("warnings_gt") is not None and not (rec.warnings > spec["warnings_gt"]):
        return False
    t = _time_to_ms(rec.start_timestamp)
    after = spec.get("start_after_ms") if "start_after_ms" in spec else _time_to_ms(spec.get("start_after"))
    before = spec.get("start_before_ms") if "start_before_ms" in spec else _time_to_ms(spec.get("start_before"))
    if after is not None and t is not None and t < after:
        return False
    if before is not None and t is not None and t > before:
        return False
    return True


def search_records(headers: List[str], query: str) -> Tuple[List[ProcessRecord], Dict[str, Any]]:
    spec = parse_query(query)
    records = [_header_to_record(h) for h in headers]
    matches = [r for r in records if _matches(r, spec)]
    return matches, spec


def _interesting_lines(lines: List[str], start: int, end: int, context_lines: int = 2) -> List[str]:
    selected = set()
    for idx in range(start, min(end, len(lines))):
        line_upper = lines[idx].upper()
        if " ERROR" in line_upper or " WARNING" in line_upper:
            for j in range(max(start, idx - context_lines), min(end, idx + context_lines + 1)):
                selected.add(j)
    return [f"L{i}: {lines[i]}" for i in sorted(selected)]


def retrieve_logfile_by_query(query: str, lines: List[str], headers: List[str]) -> str:
    if not lines or not headers:
        return "[ATTENTION] No logfile is ingested yet. Use /set-file <filename> first."

    matches, spec = search_records(headers, query)
    total_matches = len(matches)
    limit = int(spec.get("limit") or DEFAULT_LIMIT)
    limited = matches[:limit]
    mode = spec.get("return_mode", "compact")

    parts = [
        "Retrieval summary",
        f"Query: {query}",
        f"Parsed filters: {json.dumps({k: v for k, v in spec.items() if v not in [None, 'compact', DEFAULT_CONTEXT_LINES]}, ensure_ascii=False)}",
        f"Matches: {total_matches}; Returned: {len(limited)}; Mode: {mode}",
    ]
    if total_matches > limit:
        parts.append(f"[ATTENTION] Result was limited to {limit} processes. Add a narrower time/nummer/error filter for more precision.")

    returned_raw_lines = 0
    for n, rec in enumerate(limited, start=1):
        parts.append(f"\n--- Process {n} ---")
        parts.append(rec.to_header())
        if mode == "full":
            process_lines = lines[rec.start_index:rec.end_index]
            if returned_raw_lines + len(process_lines) > MAX_RETRIEVAL:
                parts.append(f"[ATTENTION] Full raw output truncated at MAX_RETRIEVAL={MAX_RETRIEVAL} lines.")
                break
            parts.append("Process log:")
            parts.extend(process_lines)
            returned_raw_lines += len(process_lines)
        elif mode == "compact":
            evidence = _interesting_lines(lines, rec.start_index, rec.end_index, int(spec.get("context_lines") or DEFAULT_CONTEXT_LINES))
            if evidence:
                parts.append("Evidence lines around errors/warnings:")
                parts.extend(evidence[:60])
            else:
                parts.append("Evidence lines: no ERROR/WARNING lines found in this process. Use 'full' if raw process lines are needed.")

    if not limited:
        parts.append("No matching process found. Try specifying Function, time range, Fehler/Error, Warning, Fahrzeugnr., Nummer, or Stopwatch threshold.")

    return "\n".join(parts)

# Backward-compatible API retained for old callers.
def search_header(headers: List[str], pattern: str) -> List[str]:
    matches = []
    for header in headers:
        try:
            if re.search(pattern, header, re.DOTALL | re.IGNORECASE):
                matches.append(header)
        except re.error:
            pass
    print(f"[DEBUG search_header] found {len(matches)} processes")
    return matches


def retrieve_logfile(matches: List[str], lines: List[str]) -> str:
    if not matches:
        return "[ATTENTION] retrieved 0 lines of Logdata"
    records = [_header_to_record(h) for h in matches]
    parts = [f"Retrieved {len(records)} matching process headers. Raw logs are omitted in first-fix mode."]
    for i, rec in enumerate(records[:DEFAULT_LIMIT], start=1):
        parts.append(f"\n--- Process {i} ---\n{rec.to_header()}")
        evidence = _interesting_lines(lines, rec.start_index, rec.end_index, DEFAULT_CONTEXT_LINES)
        if evidence:
            parts.append("Evidence lines around errors/warnings:")
            parts.extend(evidence[:60])
    return "\n".join(parts)
