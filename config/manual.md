# User Manual for Logfile Analyzer Agent:

This Agent can search in a Logfile for logged Processes and gives an analysis on it.

While searching for Processes, it uses the following Data Schema, which is part of the Process structure:

```
Process Header:
	- Start Index: [int]
    - End Index: [int]
    - Start Timestamp: [hh:mm:ss:xxx]
    - End Timestamp: [hh:mm:ss:xxx]
    - Nummer: [int]
    - Errors: [int]
    - Warnings: [int]
```

## Operation:

**Load a Logfile into the thread (chat window):**

Use `Load Logfile` to select a Logfile from the Explorer or type `/set-file {Filename} `. 
The Agent will automatically start ingesting the Logfile. After ingesting you can write search queries.
The Logfile persists in the thread until its being overwritten by loading a new Logfile or the server is being resetted.

**Select retrieval method**

The retrieval method determines how complex the retrieval (search) is.
By default the Agent selects the retrieval method automatically, based on the query classification,
however, you can override the classification and pick your retrievl method as follows:

| Button | Command | Description |
| --- | --- | --- |
| No Retrieval | /classify A | No search is being performed. the Agent is using only the context (current chat history) |
| Simple Retrieval | /classify B | One or few searches. the Agent does **not** have access to the context while searching |
| Deep Retrieval | /classify C | Multi step searches with planning and self correcting mechanisms |

Please consider that a more complex retrieval returns a more accurate answer but therefore takes more time to generate an answer.

**Clear Context**

You can clear the Context (chat history) by clicking on `Clear Context` or typing `/clear-context`.
This way the chat gets wiped, while the Logfile persists and dont need to be ingested again.
It is recommended to use this tool, if you work on the same Logfile but change the topic, or the Agent generates hallucinating answers due to a bloated context window.

**Manual**

It opens this message.

**Troubleshooting**

If the Agent seems to get stuck in generating and the `Cancel` button doesnt react, first try restart the agent-chat-ui server.

- Stop and restart the server in the terminal: 1. `ctrl + C` 2. `pnpm dev`
- Wait till the server is up and reload the ,page in the Browser

If a server restart doesnt help, you must reset the langgraph-server:

- Stop the server in the terminal by spamming `ctrl + C`
- Navigate to .../LogfileAnalyzer/langgraph-server/
- Delete the .langgraph_api/ folder
- Restart the server in the terminal: `uv run langgraph dev --no-reload --no-browser`
- Reopen the agent-chat-ui in the browser with the root URL `localhost:3000`

Note: all threads and messages get deleted during this process.

> For more Information see INFO.md and README.md
