import re
import os
import tempfile
import json
import sys
import ast
import operator

_BASE_TYPES = {
    "integer", "logic", "reg", "wire", "bit", "byte",
    "shortint", "int", "longint", "signed", "unsigned",
}

_PARAM_NAME_VALUE_RE = re.compile(r"^(\w+)\s*=\s*(.+)$")
_BARE_INT_RE = re.compile(r"^-?\d+$")

_SAFE_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Div: operator.floordiv,
}


def _safe_eval_int(expr):
    """Evaluate a plain integer arithmetic expression without exec/eval.

    Only +, -, *, /, parens and integer literals are allowed; anything else
    (sized literals, function calls, unresolved names) returns None.
    """
    try:
        node = ast.parse(expr, mode="eval").body
    except SyntaxError:
        return None
    return _eval_ast_node(node)


def _eval_ast_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_BINOPS:
        left = _eval_ast_node(node.left)
        right = _eval_ast_node(node.right)
        if left is None or right is None:
            return None
        return _SAFE_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _eval_ast_node(node.operand)
        return None if value is None else -value
    return None


class VerilogWikiParser(object):
    def __init__(self, paths, verbose=0, ci=False, json_graph=False, json_graph_file=None, print_errors=False, exclude=None, dry_run=False):
        self.paths = paths
        self.modules = {}
        self.called_by = {}
        self.modified_files = []
        self.verbose = verbose
        self.ci = ci
        self.json_graph = json_graph
        self.json_graph_file = json_graph_file
        self.print_errors = print_errors
        self.exclude = exclude or []
        self.issues = []
        self.dry_run = dry_run

    # -------------------------
    # CLEAN COMMENTS
    # -------------------------
    def clean(self, text):
        text = re.sub(r"//[^\n]*", "\n", text)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return text

    # -------------------------
    # `define RESOLUTION (single-file only, no `include)
    # -------------------------
    def resolve_defines(self, text):
        defines = dict(re.findall(r"^\s*`define\s+(\w+)\s+(.+?)\s*$", text, flags=re.M))
        if not defines:
            return text
        return re.sub(r"`(\w+)", lambda m: defines.get(m.group(1), m.group(0)), text)

    def _resolve_parameter_expr(self, expr, known_values):
        substituted = expr
        for name, value in known_values.items():
            substituted = re.sub(rf"\b{re.escape(name)}\b", str(value), substituted)
        return _safe_eval_int(substituted)

    def _format_parameter(self, keyword, raw):
        param_str = re.sub(rf"\b{keyword}\b", "", raw).strip()
        param_str = re.sub(
            rf"^({'|'.join(_BASE_TYPES)})\s+", "", param_str
        ).strip()
        return param_str

    def _strip_verilog_attributes(self, port_block):
        """Remove Verilog attributes like (*mark_debug="true",DONT_TOUCH="TRUE"*)
        from the port block to prevent comma-containing attributes from breaking
        the port splitting logic.
        """
        return re.sub(r"\(\*[^*]*\*\)\s*", "", port_block)

    # -------------------------
    # PARSING
    # -------------------------
    def extract_module_and_ports(self, text):
        pattern = r"module\s+(\w+)\s*(#\s*\((.*?)\))?\s*\((.*?)\)\s*;"
        m = re.search(pattern, text, flags=re.S)
        if not m:
            return None

        mod_name = m.group(1)
        param_block = m.group(3) or ""
        port_block = m.group(4)
        port_block = self._strip_verilog_attributes(port_block)

        inputs, outputs, inouts = [], [], []
        parameters = []
        known_values = {}

        for p in re.split(r",\s*\n|,\s*", param_block):
            p = p.strip()
            is_localparam = p.startswith("localparam")
            if not (p.startswith("parameter") or is_localparam):
                continue

            keyword = "localparam" if is_localparam else "parameter"
            param_str = self._format_parameter(keyword, p)

            display = param_str
            name_value = _PARAM_NAME_VALUE_RE.match(param_str)
            if name_value:
                pname, pexpr = name_value.group(1), name_value.group(2).strip()
                if _BARE_INT_RE.match(pexpr):
                    known_values[pname] = int(pexpr)
                else:
                    resolved = self._resolve_parameter_expr(pexpr, known_values)
                    if resolved is not None:
                        known_values[pname] = resolved
                        display = f"{pname} = {pexpr}  (= {resolved})"
                    else:
                        display = f"{pname} = {pexpr}  (unresolved)"

            if is_localparam:
                display = f"{display} (localparam)"
            parameters.append(display)

        ports = re.split(r",\s*\n|,\s*", port_block)

        current_direction = None
        for p in ports:
            p = p.strip()
            if not p:
                continue

            tokens = p.split()
            if not tokens:
                continue

            name = tokens[-1]
            type_tokens = [t for t in tokens[:-1] if t not in ("input", "output", "inout")]

            if "input" in tokens:
                current_direction = "input"
            elif "output" in tokens:
                current_direction = "output"
            elif "inout" in tokens:
                current_direction = "inout"

            width = ""
            custom_type = ""
            width_tokens = []
            in_width = False

            for t in type_tokens:
                if t.startswith("["):
                    in_width = True
                    width_tokens = [t]
                    if t.endswith("]"):
                        width = " ".join(width_tokens)
                        width_tokens = []
                        in_width = False
                elif in_width:
                    width_tokens.append(t)
                    if t.endswith("]"):
                        width = " ".join(width_tokens)
                        width_tokens = []
                        in_width = False
                elif t not in _BASE_TYPES:
                    custom_type = t

            if width:
                display = f"{name} {width}"
            elif custom_type:
                display = f"{name} ({custom_type})"
            else:
                display = name

            if current_direction == "input":
                inputs.append(display)
            elif current_direction == "output":
                outputs.append(display)
            elif current_direction == "inout":
                inouts.append(display)

        return {
            "name": mod_name,
            "inputs": inputs,
            "outputs": outputs,
            "inouts": inouts,
            "parameters": parameters
        }

    def remove_module_header(self, text):
        return re.sub(r"\bmodule\b[^;]*;", "", text)

    def extract_calls(self, text, known_modules, current_module):
        calls = set()
        text = self.remove_module_header(text)

        pattern = r"\b(\w+)\s*(?:#\s*\(.*?\))?\s+\w+\s*\("
        for m in re.finditer(pattern, text, flags=re.S):
            mod_name = m.group(1)
            if mod_name in known_modules:
                calls.add(mod_name)

        return sorted(list(calls))

    _TB_SUFFIXES = ("_tb.v", "_tb.sv", "_bench.v", "_bench.sv", "_testbench.v", "_testbench.sv")
    _RTL_EXTENSIONS = (".v", ".sv")

    def _is_rtl_file(self, filename):
        return (
            any(filename.endswith(ext) for ext in self._RTL_EXTENSIONS)
            and not any(filename.endswith(s) for s in self._TB_SUFFIXES)
        )

    # -------------------------
    # SCAN
    # -------------------------
    def scan(self):
        file_texts = {}
        all_files = []

        def is_excluded(path):
            for ex in self.exclude:
                if ex in path:
                    return True
            return False

        for p in self.paths:
            if os.path.isfile(p):
                if not is_excluded(p):
                    all_files.append(p)
            else:
                for root, dirs, files in os.walk(p):
                    dirs[:] = [d for d in dirs if not is_excluded(os.path.join(root, d))]
                    if is_excluded(root):
                        continue
                    for f in files:
                        if self._is_rtl_file(f):
                            full_path = os.path.join(root, f)
                            if not is_excluded(full_path):
                                all_files.append(full_path)

        for path in all_files:
            with open(path, "r") as fh:
                text = self.clean(fh.read())
            text = self.resolve_defines(text)

            file_texts[path] = text

            mod = self.extract_module_and_ports(text)
            if not mod:
                continue

            self.modules[mod["name"]] = {
                "file": path,
                "calls": [],
                "inputs": mod["inputs"],
                "outputs": mod["outputs"],
                "inouts": mod["inouts"],
                "parameters": mod["parameters"]
            }

        known_modules = set(self.modules.keys())

        for path, text in file_texts.items():
            mod = self.extract_module_and_ports(text)
            if not mod:
                continue

            mod_name = mod["name"]
            self.modules[mod_name]["calls"] = self.extract_calls(
                text, known_modules, mod_name
            )

        self.build_called_by()

    def build_called_by(self):
        for mod in self.modules:
            self.called_by[mod] = []

        for caller, data in self.modules.items():
            for callee in data["calls"]:
                if callee in self.called_by:
                    self.called_by[callee].append(caller)

    # -------------------------
    # EXISTING MD PARSE
    # -------------------------
    def parse_existing_sections(self, path):
        if not os.path.exists(path):
            return {}

        with open(path) as f:
            content = f.read()

        sections = {}
        for sec in ["Description", "Parameters", "Inputs", "Outputs", "Inouts", "Calls", "Called By"]:
            m = re.search(rf"## {sec}\n(.*?)(\n##|\Z)", content, re.S)
            if m:
                sections[sec] = m.group(1).strip()

        return sections

    # -------------------------
    # DIFF
    # -------------------------
    def diff_lists(self, old, new):
        old_set = set(old)
        new_set = set(new)
        return len(new_set - old_set), len(old_set - new_set)

    # -------------------------
    # MARKDOWN
    # -------------------------
    def generate_markdown(self, out_dir):
        if not self.dry_run:
            os.makedirs(out_dir, exist_ok=True)
        
        managed_sections = ["Parameters", "Inputs", "Outputs", "Inouts", "Calls", "Called By"]

        for mod, data in self.modules.items():
            fname = os.path.join(out_dir, f"{mod}.md")

            old_content = ""
            if os.path.exists(fname):
                with open(fname) as f:
                    old_content = f.read()

            old_sections = self.parse_existing_sections(fname)
            desc = old_sections.get("Description", "TODO: Add description")

            if desc.startswith("TODO"):
                self.issues.append(f"{mod}: missing description")

            def format_list(lst):
                return "\n".join([f"- {x}" for x in lst]) if lst else "- None"

            new_sections = {
                "Parameters": format_list(data["parameters"]),
                "Inputs": format_list(data["inputs"]),
                "Outputs": format_list(data["outputs"]),
                "Inouts": format_list(data["inouts"]),
                "Calls": format_list([f"[{c}]({c}.md)" for c in data["calls"]]),
                "Called By": format_list([f"[{c}]({c}.md)" for c in self.called_by.get(mod, [])]),
            }

            # DIFF LOGIC
            diffs = {}
            for key in ["Parameters", "Inputs", "Outputs", "Inouts", "Calls"]:
                old_list = re.findall(r"- (.+)", old_sections.get(key, ""))
                new_list = re.findall(r"- (.+)", new_sections[key])
                add, rem = self.diff_lists(old_list, new_list)
                diffs[key] = (add, rem)

            content = ""
            if not old_content:
                content = f"# {mod}\n\n## Description\n{desc}\n\n"
                for k, v in new_sections.items():
                    content += f"## {k}\n{v}\n\n"
            else:
                content = old_content
                for sec in managed_sections:
                    new_sec_text = f"## {sec}\n{new_sections[sec]}\n"
                    pattern = rf"## {sec}\n.*?(?=\n##|\Z)"
                    if re.search(pattern, content, flags=re.S):
                        content = re.sub(pattern, new_sec_text, content, flags=re.S)
                    else:
                        content += f"\n{new_sec_text}\n"

            content = content.strip() + "\n"

            if content != old_content:
                if not self.dry_run:
                    with open(fname, "w") as f:
                        f.write(content)

                diff_str = f"{mod}: " + ", ".join([f"{k} +{a}/-{r}" for k, (a, r) in diffs.items()])
                self.modified_files.append((fname, diff_str))

    # -------------------------
    # LOGGING
    # -------------------------
    def write_log(self):
        if self.modified_files:
            if self.dry_run:
                print("\n[DRY RUN] Would write:")
                for fname, _ in self.modified_files:
                    print(f"  {fname}")
                if self.verbose >= 2:
                    print("\nDetailed section diffs:")
                    for _, diff_str in self.modified_files:
                        print(f"  {diff_str}")
            else:
                tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".log")
                tmp.write("Modified files:\n")
                for fname, _ in self.modified_files:
                    tmp.write(fname + "\n")
                tmp.write("\nDetailed section diffs:\n")
                for _, diff_str in self.modified_files:
                    tmp.write(diff_str + "\n")
                tmp.close()

                if self.verbose >= 1:
                    print("\nModified files:")
                    for fname, _ in self.modified_files:
                        print(fname)

                if self.verbose >= 2:
                    print("\nDetailed section diffs:")
                    for _, diff_str in self.modified_files:
                        print(diff_str)

                print(f"\nLog file: {tmp.name}")

        if not self.ci:
            missing_docs = [mod for mod in self.modules if any(f"{mod}: missing description" in i for i in self.issues)]
            if missing_docs:
                print("\nMissing Docs Summary Report:")
                for m in missing_docs:
                    print(f"  - {m}")

    # -------------------------
    # JSON GRAPH
    # -------------------------
    def write_json(self, out_dir):
        if not self.json_graph:
            return

        graph = {}
        for m, d in self.modules.items():
            graph[m] = {
                "calls": d["calls"],
                "called_by": self.called_by.get(m, [])
            }

        # Determine output path: use json_graph_file if set, else create graph.json in out_dir
        if self.json_graph_file:
            path = self.json_graph_file.rstrip("/")
            graph_dir = os.path.dirname(path)
            if graph_dir and not self.dry_run:
                os.makedirs(graph_dir, exist_ok=True)
        else:
            path = os.path.join(out_dir, "graph.json")
            if not self.dry_run:
                os.makedirs(out_dir, exist_ok=True)

        if not self.dry_run:
            with open(path, "w") as f:
                json.dump(graph, f, indent=2)

    def _graph_to_dot(self, graph):
        """Convert a dependency graph dict to Graphviz DOT format."""
        lines = ["digraph {", '  rankdir=LR;', '  node [shape=box];']
        for module, deps in sorted(graph.items()):
            lines.append(f'  "{module}";')
        for module, deps in sorted(graph.items()):
            for called in sorted(deps.get("calls", [])):
                lines.append(f'  "{module}" -> "{called}";')
        lines.append("}")
        return "\n".join(lines)

    def export_dot(self, out_file):
        """Export current module graph to Graphviz DOT format."""
        graph = {}
        for m, d in self.modules.items():
            graph[m] = {
                "calls": d["calls"],
                "called_by": self.called_by.get(m, [])
            }
        dot_content = self._graph_to_dot(graph)
        if not self.dry_run:
            with open(out_file, "w") as f:
                f.write(dot_content)

    def export_dot_from_file(self, json_file, dot_file):
        """Load a graph.json file and export it to Graphviz DOT format."""
        try:
            with open(json_file, "r") as f:
                graph = json.load(f)
        except FileNotFoundError:
            print(f"Error: {json_file} not found", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: {json_file} is not valid JSON", file=sys.stderr)
            sys.exit(1)

        dot_content = self._graph_to_dot(graph)
        if not self.dry_run:
            with open(dot_file, "w") as f:
                f.write(dot_content)
        print(f"Exported graph to {dot_file}")

    # -------------------------
    # CI VALIDATION
    # -------------------------
    def run_ci_checks(self):
        if not self.ci:
            return

        for mod, data in self.modules.items():
            if not data["inputs"] and not data["outputs"]:
                self.issues.append(f"{mod}: no IO")

            if mod in data["calls"]:
                self.issues.append(f"{mod}: self-instantiation")

        if self.issues:
            if not self.dry_run:
                tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix="_errors.log")
                tmp.write("CI FAIL:\n")
                for i in self.issues:
                    tmp.write(i + "\n")
                tmp.close()
                print(f"\nError log file: {tmp.name}")

            if self.print_errors or self.dry_run:
                print("\nCI FAIL:")
                for i in self.issues:
                    print(i)
            sys.exit(1)
