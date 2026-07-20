# ToDos by Development Tier

## Tier 1: Quick Wins (1-2 hours each, for V1 release)

- [X] rtllint `--list-rules` feature
	Add enumerable lint rule discovery. Currently warning IDs are preserved in inline tags (e.g. `/* Check[WIDTHEXPAND]: ... */`), but there's no machine-readable way to list all available rule IDs. A `--list-rules` flag would allow agents and users to see what checks are available and their descriptions.
	**Status:** Partially fixed by preserving rule IDs in tags; needs output format implementation.

- [X] Add a github actions template for a new repo
	GitHub Actions workflow with pre-filled `rtllint`/`rtldoc` commands and a stub `README.md`.
	**Status:** Mechanical YAML + docs, no code changes needed.

- [X] Add a Graphviz export for the dependency graph
	Parse existing `graph.json` from `--json-graph-dir` and emit DOT format for visualization. Can be a separate lightweight CLI tool.
	**Status:** Straightforward tree walk over JSON structure.

## Tier 2: Medium Complexity (2-4 hours each)

- [X] Make it runnable via a config file
	Support YAML/TOML config files for rtldoc/rtllint instead of only CLI flags.
	**Status:** Requires argparse refactoring.

- [X] `$clog2(...)` and other SystemVerilog built-in functions
	Add support for common SystemVerilog functions in rtldoc parsing.
	**Ref:** [examples/issues/ble_controller.md](examples/issues/ble_controller.md)
	**Status:** Regex-based parser improvement; scope depends on function set.

## Tier 3: Substantial Features (defer to post-V1)

- [ ] Add a new tool rtl-tbgen to generate testbench boilerplates
	Generate module testbenches for Verilog simulation or COCOTB DUT instances. Skeleton should include clock/reset generation, bus stubs, and common testbench components.
	**Legacy references (to adapt/learn from):**
	  - https://github.com/paulscherrerinstitute/TbGenerator
	  - https://github.com/xfguo/tbgen
	  - https://github.com/phillbush/tbgen
	**Status:** New tool, substantial even as skeleton.

- [ ] Cross-file `include` resolution
	Extend parser to resolve `` `include `` directives across multiple files (currently only does single-file `` `define `` substitution). Improves robustness for modules with macros in included headers.
	**Status:** Low priority; most codebases use ANSI-style ports without macro inclusion.

- [ ] MCP server wrapper
	Expose rtldoc and rtllint as MCP tools so agents (Claude, Cursor, Devin, etc.) can call them natively without subprocess invocation.
	**Ref:** examples/mcp_server_description.md for tool schema and implementation notes.
	**Status:** Requires MCP spec work and scaffolding.

## Tier 4: Future Ideas (Not in V1 Scope)

- [ ] FPGA Design Elements Generator
	Tool to generate common FPGA components (FIFOs, RAMs, shift registers, etc.) from templates or a loaded repository.(Inspired by psi-common)
	**Status:** Explore tool patterns and repository structure; deferred pending user demand.

- [ ] Revive PyVerilog? 
	Investigate whether PyVerilog can be revived or forked to support modern Verilog/SystemVerilog parsing and analysis. Could serve as a foundation for more advanced static analysis tools.
	**Status:** Research phase; no immediate plans.

- [ ] Go full Lex and Yacc
	Rewrite the parser using a formal grammar and parser generator (e.g., ANTLR, PLY) to improve robustness and maintainability. This would allow for more complex language features and better error reporting.
	**Status:** Long-term research; not in immediate scope.
	**Ref:** https://cse.iitkgp.ac.in/~bivasm/notes/LexAndYaccTutorial.pdf
	
