# MCP Server Design

## Overview

SimFlow uses Model Context Protocol (MCP) servers to provide external system access. Each server exposes a set of tools via a standardized interface.

## Server Architecture

```
MCP Server
├── server.py (tool definitions, request routing)
├── connectors/
│   ├── __init__.py
│   ├── base.py (abstract connector)
│   ├── mock.py (dry-run connector)
│   └── *.py (concrete connectors)
└── metadata.json (capability declaration)
```

## Transport

- **stdin/stdout**: Default transport for local MCP servers
- **JSON-RPC**: Request/response format

## Tool Interface

Each tool receives a params dict and returns a result dict:

```python
def handle_search(params: dict) -> dict:
    query = params.get("query", "")
    # ... implementation
    return {"status": "success", "data": {...}}
```

## Servers

### Literature Server

| Tool | Description |
|------|-------------|
| `search` | Search literature databases |
| `get_metadata` | Get metadata by DOI |

Backends: arxiv, crossref, semantic_scholar, mock

### Structure Server

| Tool | Description |
|------|-------------|
| `search` | Search structures by formula |
| `get` | Get structure by ID |

Backends: materials_project, cod, mock

### HPC Server

| Tool | Description |
|------|-------------|
| `dry_run` | Validate job script |
| `prepare` | Generate job script |
| `submit` | Submit job to scheduler |
| `status` | Check job status |

Schedulers: slurm, pbs, local, ssh

### State Server

| Tool | Description |
|------|-------------|
| `init_workflow` | Initialize workflow state |
| `read_state` | Read current state |
| `write_state` | Update state |
| `transition` | Advance to next stage |

## Authentication

Credentials are read from environment variables only:

| Variable | Service |
|----------|---------|
| `MP_API_KEY` | Materials Project |
| `S2_API_KEY` | Semantic Scholar |
| `SIMFLOW_SSH_HOST` | SSH HPC host |
| `SIMFLOW_SSH_USER` | SSH username |
| `SIMFLOW_SSH_KEY` | SSH key file path |

Missing credentials trigger graceful fallback to mock connectors.
