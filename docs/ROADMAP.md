# High-level roadmap overview

*Abstract of the `montage-mcp-server` project roadmap*

The project top level goal is to **sucessfully finish HyperFlow task execution using Montage MCP Server integrated with an external LLM**.

Expected sequence of actions:
- user prompts LLM about astronomical image mosaic
- LLM passes the question to Montage MCP Server
- Montage prepares a workflow definition
- LLM schedules workflow execution on HyperFlow (LLM native kubectl support or 3rd party Kubernetes MCP server)
- user monitors the execution progress
- the user gets the requested astronomical image mosaic

## Short term goals

### solution architecture design

The objective is to define the Montage MCP Server and HyperFlow communication architecture.

Options:
- design a solution using two MCP servers: the Montage and one supporting Kubernetes
- the LLM prepares kubectl or helm commands to execute HyperFlow task

### assess the Kubernetes MCP servers maturity

The goal is to investigate the capabilities of the Kubernetes MCP server. The objective is to determine whether it is capable of creating a HyperFlow task.

### HyperFlow task status monitoring

The objective is to inform the LLM of the task calculation status.
