# ToDos:

- [X] **BUG: Port width ranges with spaces are truncated (v0.2.3 regression - FIXED)**
	**Severity:** High — generates incomplete port documentation
	**Issue:** Port width specifications with spaces around colons (e.g., `[15 : 0]` instead of `[15:0]`) were incompletely parsed, capturing only the opening bracket and first token.
	**Root Cause (Fixed):** In `core.py:extract_module_and_ports()`:
	1. Line 159: `tokens = p.split()` splits on whitespace, breaking `[15 : 0]` into separate tokens
	2. Old code (line 176-177): Width extraction only checked `if t.startswith("[")`, capturing only first token `[15`
	3. Remaining tokens (`:`, `0]`) were lost, resulting in truncated width
	
	**Solution Implemented:**
	- Added state machine to collect ALL tokens between `[` and `]`
	- Handles both single-token `[7:0]` and multi-token `[15 : 0]` ranges
	- Preserves spacing by joining tokens: `" ".join(width_tokens)`
	- Works with parameter expressions: `[PARAM-1 : 0]`, `[PARAM_A : PARAM_B]`
	
	**Verification:**
	- ✅ 7 new tests all passing (including edge cases)
	- ✅ All 242 existing tests still pass (no regressions)
	- ✅ Real-world test on ble_ll.v: axi_awprot [2 : 0] now correctly parsed
	- ✅ Real-world test on ble_ll.v: axi_awaddr [C_S00_AXI_ADDR_WIDTH-1 : 0] now correctly parsed
	
	**Test Cases:** `tests/core/fixtures/port_widths_with_spaces.v`:
	- ✅ `[7:0]` (single token, works)
	- ✅ `[15 : 0]` (fixed — now captures full range with spaces)
	- ✅ `[C_WIDTH-1 : 0]` (fixed — parameter expressions preserved)
	- ✅ `[PARAM_A-1 : PARAM_B]` (fixed — complex expressions work)

- [X] **BUG: Backtick attribute handling breaks port parsing (v0.2.2 regression)**
	**Severity:** High — generates corrupted module documentation
	**Issue:** Lines with Verilog backtick-prefixed attributes (e.g., `KEEP_FOR_DBG) are incorrectly parsed during port extraction.
	**Root Cause:** In `core.py:extract_module_and_ports()`:
	1. `resolve_defines()` expands backticks to full attribute strings containing commas: `KEEP_FOR_DBG → (*mark_debug="true",DONT_TOUCH="TRUE"*)`
	2. Line 143 splits port block by commas, treating comma-separated attributes as separate ports
	3. Line 151-155 tokenizes malformed port entries, leaking attribute text into port names and truncating bit widths
	
	**Impact:** Port documentation becomes corrupted:
	- Attribute text leaks into port names: `ref_1pps` → `(*mark_debug="true"` + `ref_1pps (DONT_TOUCH="TRUE"*)`
	- Bit widths truncated: `axi_bresp [1:0]` → `axi_bresp [1`
	- Duplicate/orphaned entries from split attributes
	
	**Affected Files:**
	- `ble_ll.md` (new): 60+ ports mislabeled across inputs/outputs sections
	- `auxiliary_daemon.md` (new): 10+ ports mislabeled
	
	**Fix Strategy:** Strip backtick-prefixed tokens from port block before tokenization. Two approaches:
	1. **Preferred:** In `extract_module_and_ports()`, remove lines/tokens starting with backticks before splitting by commas
	2. **Alternative:** Modify `clean()` to strip backticks entirely instead of relying on `resolve_defines()` to expand them
	
	**Test Cases:** See `examples/issues/{ble_ll,auxiliary_daemon}_{old,new}.md` and reference `.v` files for actual port definitions.

- [x] Add a `--version` flag to rtllint and rtldoc to print the current version of the tool.
	Implemented: Both tools now accept `--version` flag and display version from `__version__` in `__init__.py`
	Usage: `rtldoc --version` → `rtldoc 0.2.1` | `rtllint --version` → `rtllint 0.2.1`

- [ ] Make it runnable via a config file

- [ ] Add a github actions template for a new repo, with a pre-filled `rtllint`/`rtldoc` workflow and a stub `README.md`.

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
