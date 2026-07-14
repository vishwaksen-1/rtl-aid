# ToDos:

- [ ] Add a Graphviz export for the dependency graph of callgraph. Preferably as a separate tool to work on the generated json graph.

- [ ] MCP server wrapper
	Expose rtldoc and rtllint as MCP tools so agents (Claude, Cursor, Devin, etc.) can call them natively without subprocess invocation.
	See examples/mcp_server_description.md for the proposed tool schema and implementation notes.

- [ ] rtllint `--list-rules` feature
	Add enumerable lint rule discovery. Currently warning IDs are preserved in inline tags (e.g. `/* Check[WIDTHEXPAND]: ... */`), but there's no machine-readable way to list all available rule IDs. A `--list-rules` flag would allow agents and users to see what checks are available and their descriptions.
	**From checklist.md:** Deferred as separate product decision; partially fixed by preserving rule IDs in tags.

- [ ] Cross-file `include` resolution
	Extend parser to resolve `` `include `` directives across multiple files (currently only does single-file `` `define `` substitution). This would improve robustness when module ports use macros defined in included header files.
	**From checklist.md:** Currently unsupported; single-file `define` resolution works, multi-file `include` deferred as out of scope but feasible improvement.
	**Note:** Low priority — most real-world codebases use ANSI-style ports without macro inclusion; implement only if user demand warrants complexity.
