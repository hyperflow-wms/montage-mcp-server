# High-level roadmap overview

* execute HyperFlow job based on LLM prompt processed by Montage MCP server

This final goal is to perform following test case:
- user prompts LLM about astronomical image mosaic
- LLM passes the question to Montage MCP Server
- Montage prepares workflow definition
- LLM schedules workflow execution on HyperFlow (using Montage or 3rd party Kubernetes MCP server)
- users gets the requested astronomical image mosaic

* architecture design

The objective is to conclude the Montage MCP server and HyperFlow communication.

Currently there are two options:
- implement the HyperFlow tasks execution in Montage MCP server
- design a solution using two MCP servers: Montage and one supporting Kubernetes

* assess the Kubernetes MCP servers maturity

The goal is to investigate the capabilities of Kubernetes MCP server. The objective is to conclude if they are capable of creating a HyperFlow task.

* HyperFlow task monitoring

The objective is to inform the LLM the task calculation status.
