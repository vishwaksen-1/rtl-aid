"""Configuration file support for rtldoc and rtllint.

Provides:
- Config file discovery (.rtl-aidrc.yml with upward search)
- YAML parsing and validation
- CLI argument precedence (CLI args override config file)
- Config file generation for --init-workflow
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any, List


class ConfigError(Exception):
    """Raised when config parsing, validation, or file operations fail."""
    pass


def find_config_file(
    start_dir: Optional[str] = None,
    config_flag: Optional[str] = None,
    filename: str = ".rtl-aidrc.yml"
) -> Optional[str]:
    """Search for config file with optional explicit path override.

    If config_flag is provided, use that explicit path (error if not found).
    Otherwise, search upward from start_dir (or cwd) until config found or root reached.

    Args:
        start_dir: Starting directory for upward search (default: cwd)
        config_flag: Explicit config file path from --config flag
        filename: Config filename to search for (default: .rtl-aidrc.yml)

    Returns:
        Absolute path to config file, or None if not found (only when no config_flag)

    Raises:
        ConfigError: If config_flag provided but file doesn't exist
    """
    if config_flag:
        # Explicit config flag: must exist
        config_path = Path(config_flag).resolve()
        if not config_path.is_file():
            raise ConfigError(f"Config file not found: {config_flag}")
        return str(config_path)

    # Upward search from start_dir (or cwd)
    start = Path(start_dir or os.getcwd()).resolve()

    current = start
    while True:
        candidate = current / filename
        if candidate.is_file():
            return str(candidate)

        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None

        current = parent


def parse_config(filepath: str) -> Dict[str, Any]:
    """Parse YAML config file.

    Args:
        filepath: Path to .rtl-aidrc.yml file

    Returns:
        Dict with "rtldoc" and/or "rtllint" keys and their settings

    Raises:
        ConfigError: On malformed YAML or I/O errors
    """
    try:
        with open(filepath, "r") as f:
            content = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"Config file not found: {filepath}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {e}") from e
    except Exception as e:
        raise ConfigError(f"Error reading config file: {e}") from e

    # Empty or bare file returns empty dict
    if content is None:
        return {}

    if not isinstance(content, dict):
        raise ConfigError(f"Config file must contain a YAML dict, got {type(content).__name__}")

    # Coerce single strings to lists for known list options
    LIST_OPTIONS_RTLDOC = {"dir", "file", "exclude"}
    LIST_OPTIONS_RTLLINT = {"file", "include"}

    if "rtldoc" in content and isinstance(content["rtldoc"], dict):
        for key in LIST_OPTIONS_RTLDOC:
            if key in content["rtldoc"]:
                content["rtldoc"][key] = _coerce_to_list(content["rtldoc"][key])

    if "rtllint" in content and isinstance(content["rtllint"], dict):
        for key in LIST_OPTIONS_RTLLINT:
            if key in content["rtllint"]:
                content["rtllint"][key] = _coerce_to_list(content["rtllint"][key])

    return content


def validate_config(config: Dict[str, Any]) -> None:
    """Validate config structure and option types.

    Args:
        config: Parsed config dict from parse_config()

    Raises:
        ConfigError: If validation fails (type mismatch, unknown keys, etc.)
    """
    # Known option schemas for rtldoc and rtllint
    RTLDOC_OPTIONS = {
        "dir": (list, str),  # Can be list or single string (coerced)
        "file": (list, str),  # Can be list or single string (coerced)
        "out": (str,),
        "verbose": (int, bool),
        "ci": (bool,),
        "print_errors": (bool,),
        "json_graph": (bool,),
        "json_graph_file": (str, type(None)),
        "export_dot": (str, type(None)),
        "exclude": (list, str),  # Can be list or single string (coerced)
        "dry_run": (bool,),
    }

    RTLLINT_OPTIONS = {
        "file": (list, str),  # Can be list or single string (coerced)
        "include": (list, str),  # Can be list or single string (coerced)
        "include_dirs": (list, str),  # Alternative key name
        "verbose": (bool,),
        "dry_run": (bool,),
    }

    # Validate rtldoc section
    if "rtldoc" in config:
        rtldoc = config["rtldoc"]
        if not isinstance(rtldoc, dict):
            raise ConfigError(f"rtldoc section must be a dict, got {type(rtldoc).__name__}")

        for key, value in rtldoc.items():
            if key not in RTLDOC_OPTIONS:
                # Unknown option - could warn or error depending on implementation
                # For now, warn but don't fail
                pass
            else:
                allowed_types = RTLDOC_OPTIONS[key]
                if not isinstance(value, allowed_types):
                    raise ConfigError(
                        f"rtldoc.{key}: expected {allowed_types}, got {type(value).__name__}"
                    )

        # Check mutually exclusive: dir and file
        if "dir" in rtldoc and "file" in rtldoc:
            raise ConfigError(
                "rtldoc: 'dir' and 'file' are mutually exclusive (choose one)"
            )

    # Validate rtllint section
    if "rtllint" in config:
        rtllint = config["rtllint"]
        if not isinstance(rtllint, dict):
            raise ConfigError(f"rtllint section must be a dict, got {type(rtllint).__name__}")

        for key, value in rtllint.items():
            if key not in RTLLINT_OPTIONS:
                # Unknown option - warn but don't fail
                pass
            else:
                allowed_types = RTLLINT_OPTIONS[key]
                if not isinstance(value, allowed_types):
                    raise ConfigError(
                        f"rtllint.{key}: expected {allowed_types}, got {type(value).__name__}"
                    )


def _coerce_to_list(value: Any) -> Optional[List[str]]:
    """Coerce single string values to list, keep lists as-is, None stays None."""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value]
    return value


def merge_config_with_args(
    config: Dict[str, Any],
    cli_args: Dict[str, Any],
    section: str,
    list_options: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Merge config file values with CLI arguments.

    CLI arguments take precedence. Returns merged config for the given section.

    Args:
        config: Parsed config dict (or empty dict if no config file)
        cli_args: Dict of CLI arguments
        section: "rtldoc" or "rtllint"
        list_options: Optional list of option names that are lists (not used in this impl)

    Returns:
        Merged config dict for section with CLI args taking precedence
    """
    if not config or section not in config:
        section_config = {}
    else:
        section_config = dict(config.get(section, {}))

    # Map some CLI arg names to config keys
    # e.g., cli_args["v"] -> verbose, cli_args["include_dirs"] -> include
    arg_mapping = {
        "v": "verbose",
        "include_dirs": "include",
    }

    # Merge CLI args into config (CLI wins)
    for cli_key, cli_value in cli_args.items():
        if cli_value is None:
            # Unset CLI arg - use config value if present
            continue

        mapped_key = arg_mapping.get(cli_key, cli_key)

        # Skip default/falsy values (they mean "not set" on CLI)
        if cli_key in ("v", "verbose") and cli_value == 0:
            # Default verbose value (0) - skip, let config value be used
            continue
        elif isinstance(cli_value, bool) and not cli_value:
            # False boolean from CLI (default) - skip, let config value be used
            continue
        elif isinstance(cli_value, list) and not cli_value:
            # Empty list from CLI - skip
            continue
        elif isinstance(cli_value, str) and not cli_value:
            # Empty string from CLI - skip
            continue

        # Apply CLI value (override config)
        section_config[mapped_key] = cli_value

        # Handle mutually exclusive options
        if section == "rtldoc":
            if cli_key == "file" and cli_value:
                # If file is set, remove dir
                section_config.pop("dir", None)
            elif cli_key == "dir" and cli_value:
                # If dir is set, remove file
                section_config.pop("file", None)

    return section_config


def load_config_for_rtldoc(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load rtldoc configuration from found .rtl-aidrc.yml.

    Args:
        config_file: Optional explicit config file path

    Returns:
        Dict with rtldoc config options, or empty dict if no config found
    """
    try:
        found_file = find_config_file(config_flag=config_file)
        if not found_file:
            return {}

        config = parse_config(found_file)
        validate_config(config)

        # Return rtldoc section or empty dict
        return config.get("rtldoc", {})
    except ConfigError:
        # Re-raise config errors
        raise
    except Exception as e:
        raise ConfigError(f"Error loading rtldoc config: {e}") from e


def load_config_for_rtllint(config_file: Optional[str] = None) -> Dict[str, Any]:
    """Load rtllint configuration from found .rtl-aidrc.yml.

    Args:
        config_file: Optional explicit config file path

    Returns:
        Dict with rtllint config options, or empty dict if no config found
    """
    try:
        found_file = find_config_file(config_flag=config_file)
        if not found_file:
            return {}

        config = parse_config(found_file)
        validate_config(config)

        # Return rtllint section or empty dict
        return config.get("rtllint", {})
    except ConfigError:
        # Re-raise config errors
        raise
    except Exception as e:
        raise ConfigError(f"Error loading rtllint config: {e}") from e


def create_config_file(output_path: str, template_content: str) -> None:
    """Create a new config file with template content.

    Args:
        output_path: Path where to write .rtl-aidrc.yml
        template_content: Template config content

    Raises:
        ConfigError: If file already exists or write fails
    """
    output_file = Path(output_path)

    if output_file.exists():
        raise ConfigError(f"Config file already exists: {output_path}")

    try:
        # Create parent directories if needed
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w") as f:
            f.write(template_content)
    except Exception as e:
        raise ConfigError(f"Error creating config file: {e}") from e
