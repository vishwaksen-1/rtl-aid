import argparse
import os
import sys
from importlib import resources
from . import __version__
from .core import VerilogWikiParser
from .config import find_config_file, parse_config, validate_config, merge_config_with_args, create_config_file, ConfigError

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
        "--json-graph",
        action="store_true",
        help="Generate dependency graph as JSON"
    )

    parser.add_argument(
        "--json-graph-file",
        metavar="FILE",
        help="JSON file to write/update graph to (used with --json-graph; creates/updates FILE)"
    )

    parser.add_argument(
        "--export-dot",
        metavar="FILE",
        help="Export dependency graph as Graphviz DOT file"
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

    # Handle graph-only mode: load existing graph.json and export to DOT
    if args.json_graph_file and args.export_dot and not args.dir and not args.file:
        v = VerilogWikiParser(
            [],
            verbose=args.v,
            ci=False,
            json_graph=False,
            json_graph_file=args.json_graph_file,
            print_errors=args.print_errors,
            exclude=args.exclude,
            dry_run=args.dry_run,
        )
        v.export_dot_from_file(args.json_graph_file, args.export_dot)
        return

    if not args.dir and not args.file:
        parser.error("one of the arguments -d/--dir -f/--file is required")

    paths = args.dir if args.dir else args.file

    v = VerilogWikiParser(
        paths,
        verbose=args.v,
        ci=args.ci,
        json_graph=args.json_graph,
        json_graph_file=args.json_graph_file,
        print_errors=args.print_errors,
        exclude=args.exclude,
        dry_run=args.dry_run,
    )
    v.scan()
    v.generate_markdown(args.out)
    v.write_json(args.out)
    if args.export_dot:
        v.export_dot(args.export_dot)
    v.write_log()
    v.run_ci_checks()

    total = len(v.modules)
    written = len(v.modified_files)
    unchanged = total - written
    action = "would be written" if args.dry_run else "written"
    print(f"\n{total} module(s) processed — {written} doc(s) {action}, {unchanged} unchanged")

if __name__ == "__main__":
    main()
