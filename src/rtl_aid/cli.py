import argparse
import os
import sys
import glob
import json
from importlib import resources
from . import __version__
from .core import VerilogWikiParser
from .config import find_config_file, parse_config, validate_config, merge_config_with_args, create_config_file, ConfigError

def expand_glob_patterns(paths, base_dir=None):
    """Expand glob patterns in path list, relative to base_dir.

    If a path contains wildcards, expand it using glob.
    Otherwise, return the path as-is.

    Relative paths are resolved relative to base_dir (if provided).
    Absolute paths are used as-is regardless of base_dir.

    Args:
        paths: List of paths, may contain glob patterns
        base_dir: Base directory for resolving relative paths (typically config file dir)

    Returns:
        list: Expanded paths (glob patterns replaced with matched files)
    """
    if not paths:
        return []

    expanded = []
    for path in paths:
        # Resolve relative paths relative to base_dir
        if base_dir and not os.path.isabs(path):
            resolved_path = os.path.join(base_dir, path)
        else:
            resolved_path = path

        # Check if path contains glob wildcards
        if any(char in resolved_path for char in ['*', '?', '[']):
            # Expand glob pattern
            matches = glob.glob(resolved_path, recursive=True)
            if matches:
                expanded.extend(sorted(matches))
            else:
                # No matches found, keep the original path (let VerilogWikiParser handle the error)
                expanded.append(resolved_path)
        else:
            # Not a glob pattern, keep as-is
            expanded.append(resolved_path)

    return expanded


def init_workflow(output_dir: str = ".") -> None:
    """Create GitHub Actions workflow and config file templates.

    Args:
        output_dir: Directory to create files in (default: current directory)

    Raises:
        SystemExit: On error or if files already exist
    """
    workflow_dir = os.path.join(output_dir, ".github", "workflows")
    workflow_file = os.path.join(workflow_dir, "rtl-checks.yml")
    config_file = os.path.join(output_dir, ".rtl-aidrc.yml")

    # Check for existing files
    if os.path.exists(workflow_file):
        print(f"Error: {workflow_file} already exists", file=sys.stderr)
        sys.exit(1)

    if os.path.exists(config_file):
        print(f"Error: {config_file} already exists", file=sys.stderr)
        sys.exit(1)

    try:
        template_content = resources.read_text("rtl_aid.templates.workflows", "rtl-checks.yml")
        config_template = resources.read_text("rtl_aid.templates", "rtl-aidrc-template.yml")
    except FileNotFoundError as e:
        print(f"Error: template not found: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        os.makedirs(workflow_dir, exist_ok=True)
        with open(workflow_file, "w") as f:
            f.write(template_content)
        print(f"Created {workflow_file}")

        with open(config_file, "w") as f:
            f.write(config_template)
        print(f"Created {config_file}")
    except Exception as e:
        print(f"Error creating files: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(prog="rtldoc")

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "--init-workflow",
        action="store_true",
        help="Create GitHub Actions workflow template (.github/workflows/rtl-checks.yml) and config file (.rtl-aidrc.yml)"
    )

    parser.add_argument(
        "--config",
        metavar="FILE",
        help="Config file path (.rtl-aidrc.yml) — default searches upward from current directory"
    )

    group = parser.add_mutually_exclusive_group(required=False)
    
    group.add_argument(
        "-d", "--dir",
        nargs="+",
        metavar="DIR",
        help="One or more directories to recursively scan for Verilog (.v) files"
    )
    
    group.add_argument(
        "-f", "--file",
        nargs="+",
        metavar="FILE",
        help="One or more specific Verilog files to parse (no directory traversal)"
    )

    group.add_argument(
        "--from-graph",
        metavar="FILE",
        help="Skip scanning; load an existing JSON graph from FILE and write it via --export-graph target(s)"
    )

    parser.add_argument(
        "-o", "--out",
        default="temp/docs/modules",
        metavar="OUT_DIR",
        help="Output directory for generated markdown docs (default: temp/docs/modules)"
    )
    
    parser.add_argument(
        "-v",
        action="count",
        default=0,
        help="Verbose mode: -v shows modified files, -vv shows detailed section diffs"
    )
    
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Enable CI mode: fail (exit 1) on issues like missing docs, no IO, or invalid structures"
    )
    
    parser.add_argument(
        "--print-errors",
        action="store_true",
        help="Print errors to stdout in addition to the error log file"
    )
    
    parser.add_argument(
        "--export-graph",
        action="append",
        metavar="FILE",
        help="Export the dependency graph to FILE. Format is inferred from the "
             "extension (.json or .dot). Repeatable. A bare filename with no "
             "directory component is written inside the output directory."
    )

    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="EXCLUDE",
        help="Directories or files to exclude from scanning"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be written without touching any files"
    )

    args = parser.parse_args()

    if args.init_workflow:
        init_workflow(".")
        sys.exit(0)

    # Validate --export-graph / --from-graph extensions up front, before any
    # config loading or scanning — fail fast on an unsupported format.
    for target in args.export_graph or []:
        if os.path.splitext(target)[1].lower() not in (".json", ".dot"):
            parser.error(f"--export-graph: unsupported extension in {target!r} (use .json or .dot)")
    if args.from_graph and os.path.splitext(args.from_graph)[1].lower() != ".json":
        parser.error(f"--from-graph: expected a .json file, got {args.from_graph!r}")

    # Load config file if present
    full_config = {}
    config_file_dir = None  # Directory of config file (for path resolution)
    try:
        config_file = find_config_file(config_flag=args.config)
        if config_file:
            full_config = parse_config(config_file)
            validate_config(full_config)
            # Store config file directory for relative path resolution
            config_file_dir = os.path.dirname(os.path.abspath(config_file))
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Merge CLI args with config (CLI takes precedence)
    cli_args = {
        "dir": args.dir,
        "file": args.file,
        "out": args.out if args.out != "temp/docs/modules" else None,
        "v": args.v,
        "ci": args.ci,
        "print_errors": args.print_errors,
        "export_graph": args.export_graph,
        "from_graph": args.from_graph,
        "exclude": args.exclude,
        "dry_run": args.dry_run,
    }

    merged = merge_config_with_args(full_config, cli_args, "rtldoc")

    # Standalone conversion mode: --from-graph explicitly requests skipping
    # the scan entirely. This is the whole point of the flag — a project's
    # config file will typically set 'dir' for normal doc-gen runs, and
    # --from-graph on the CLI must still short-circuit scanning without
    # requiring the user to edit or omit their config. (The only case that
    # can't happen is -d/-f *on the CLI* alongside --from-graph — argparse's
    # mutually-exclusive group already rejects that combination.)
    if merged.get("from_graph"):
        export_targets = merged.get("export_graph") or []
        if not export_targets:
            parser.error("--from-graph requires at least one --export-graph target")

        from_graph = merged.get("from_graph")
        if config_file_dir and not os.path.isabs(from_graph):
            from_graph = os.path.join(config_file_dir, from_graph)

        try:
            with open(from_graph, "r") as f:
                graph = json.load(f)
        except FileNotFoundError:
            print(f"Error: {from_graph} not found", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: {from_graph} is not valid JSON", file=sys.stderr)
            sys.exit(1)

        out = merged.get("out", "temp/docs/modules")
        if config_file_dir and not os.path.isabs(out):
            out = os.path.join(config_file_dir, out)

        v = VerilogWikiParser(
            [],
            verbose=merged.get("verbose", 0),
            ci=False,
            export_graph=export_targets,
            print_errors=merged.get("print_errors", False),
            exclude=merged.get("exclude"),
            dry_run=merged.get("dry_run", False),
        )
        v.export_graphs(out, graph=graph)
        for target in export_targets:
            print(f"Exported graph to {v._resolve_export_path(target, out)}")
        return

    # Require dir or file from either CLI or config
    if not merged.get("dir") and not merged.get("file"):
        parser.error("one of the arguments -d/--dir -f/--file is required (or specify in config file)")

    # Get paths and expand glob patterns
    # Use config file directory as base for relative paths
    paths = merged.get("dir") if merged.get("dir") else merged.get("file")
    paths = expand_glob_patterns(paths, base_dir=config_file_dir)
    out = merged.get("out", "temp/docs/modules")

    # Resolve output directory relative to config file if present
    if config_file_dir and not os.path.isabs(out):
        out = os.path.join(config_file_dir, out)

    v = VerilogWikiParser(
        paths,
        verbose=merged.get("verbose", 0),
        ci=merged.get("ci", False),
        export_graph=merged.get("export_graph"),
        print_errors=merged.get("print_errors", False),
        exclude=merged.get("exclude"),
        dry_run=merged.get("dry_run", False),
    )
    v.scan()
    v.generate_markdown(out)
    v.export_graphs(out)
    v.write_log()
    v.run_ci_checks()

    total = len(v.modules)
    written = len(v.modified_files)
    unchanged = total - written
    action = "would be written" if args.dry_run else "written"
    print(f"\n{total} module(s) processed — {written} doc(s) {action}, {unchanged} unchanged")

if __name__ == "__main__":
    main()
