# ToDos:

- [x] rtllint bug
	```
	// lint-test: verilator --lint-only -Wall -Irtl/core/ rtl/afe/clk_cross_bus.v
	// tb-test: tba
	```
	Include directories `-I` should have a space,
	It should be `-I rtl/core/` instead of `-Irtl/core/`.

- [x] rtllint feature check
	- When it adds lint-test, tb-test commands on the top, it should check if it's doing a dubplicate job, and behave appropriately.


- [ ] Add a Graphviz export for the dependency graph of callgraph. Preferably as a separate tool to work on the generated json graph.

- [ ] MCP server wrapper
	Expose rtldoc and rtllint as MCP tools so agents (Claude, Cursor, Devin, etc.) can call them natively without subprocess invocation.
	See examples/mcp_server_description.md for the proposed tool schema and implementation notes.

## Found during checklist.md review (2026-07-02)

- [ ] rtllint `-I`/`--include` flag broken on Verilator 5.048 (regression, contradicts closed item above)
	`_run_lint()` in `src/rtl_aid/lint.py` builds the include arg as `["-I", d]` (space-separated).
	On Verilator 5.048 this is NOT accepted as an include path — verilator parses the directory
	as a bare positional module-search request and hard-errors:
	```
	$ rtllint -I incdir toppw.v
	%Error: Cannot find file containing module: 'incdir'
	```
	Only the attached form `-I<dir>` (no space) works:
	```
	$ verilator --lint-only -Wall -Iincdir toppw.v   # works
	$ verilator --lint-only -Wall -I incdir toppw.v  # fails
	```
	This is the opposite of the fix in the "rtllint bug" item above (`-Irtl/core/` → `-I rtl/core/`),
	which was presumably correct for whatever Verilator version was used at the time but is broken on
	5.048. Fix: build the flag as a single token (`f"-I{d}"`) instead of two argv entries. Any project
	currently passing `-I` to rtllint gets a hard failure instead of a lint result.

- [ ] rtldoc never reads doc-comments from source (checklist "High Risk" items 6-7)
	`generate_markdown()` in `core.py` only ever writes `"TODO: Add description"` for new modules and
	otherwise preserves whatever a human already wrote in `## Description`. There is no parsing of any
	doc-comment annotation syntax from RTL source — the feature doesn't exist. Either build it, or stop
	implying (in README/AGENTS.md) that descriptions can be comment-driven.

- [ ] rtllint has no discoverable/stable rule set (checklist items 12, 77)
	rtllint has no rules of its own — it shells out to `verilator --lint-only -Wall` and tags whatever
	comes back, so its "rule set" is whatever `-Wall` happens to enable on the installed Verilator
	version. Docs don't enumerate rule IDs. Worse: `parse_lint_output()` (`lint.py:56`) discards the
	`%Warning-<ID>` prefix and keeps only the free-text message, so the inline `/* Check: */` tag has no
	stable ID an agent could grep for or cite when justifying a suppression. Consider tagging as
	`/* Check[WIDTHEXPAND]: ... */`.

- [ ] rtllint doesn't check sensitivity-list completeness (checklist item 24)
	`always @(a) y = a & b;` with `b` missing from the sensitivity list lints clean under
	`verilator --lint-only -Wall` (5.048) — no warning. The `always_comb`-over-`always @*` advantage
	assumed in AGENTS.md/README isn't actually enforced by rtllint.

- [ ] rtllint doesn't flag unlabeled `generate` blocks (checklist items 27, 75)
	A `generate ... endgenerate` containing an unnamed `begin ... end` lints clean. If labeled generate
	blocks are meant to be mandatory, rtllint currently provides zero enforcement of it.

- [ ] rtldoc never renders port/parameter widths or types (checklist items 62, 65, 66)
	`extract_module_and_ports()` (`core.py`) keeps only `tokens[-1]` (the bare identifier) per port —
	bit-width (`[7:0]`), packed-struct type names, and enum types are all discarded before they ever
	reach the doc. Every port list in generated Markdown is names-only, e.g. `- data`, never
	`- data [7:0]`. Same root cause means struct- and enum-typed ports also render with zero type info.

- [ ] rtldoc copies parameter expressions verbatim instead of resolving them (checklist item 63)
	`parameter DERIVED = BASE * 2` renders in the doc as `DERIVED = BASE * 2`, not `8` — no expression
	evaluation happens.

- [ ] rtldoc silently drops `localparam` entries (checklist item 64)
	`extract_module_and_ports()` only keeps params where `p.startswith("parameter")`. `localparam` lines
	never match this and disappear from the generated doc entirely — not shown as omitted, not shown
	at all, no distinct section either.

- [ ] rtldoc silently drops macro-driven port declarations (checklist item 57)
	Ports declared via a macro standing in for the direction keyword:
	```verilog
	`define IO_IN input
	module m(`IO_IN clk, `IO_IN [7:0] data, output valid);
	```
	produce a doc with `Inputs: - None` — `clk` and `data` vanish with no warning. rtldoc does no
	`` `define ``/`` `include `` preprocessing before parsing ports; it only cosmetically strips
	backtick tokens followed by whitespace (`re.sub(r"`\w+\s+", "", p)`), which doesn't cover this case
	and produces a silently wrong doc rather than a visible error.
