"""
SystemVerilog built-in functions support for parameter evaluation.

Provides configuration loading and evaluation of functions like $clog2, $bits, $size, $high.
"""

import os
import re
import yaml
import math
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Get the path to packaged functions.yaml
PACKAGED_FUNCTIONS_PATH = Path(__file__).parent / "config" / "functions.yaml"


def load_functions_config(file_path):
    """Load functions configuration from YAML file.

    Args:
        file_path: Path to functions.yaml file

    Returns:
        dict: Functions configuration with 'functions' and 'metadata' keys,
              or None if file not found or invalid
    """
    if not file_path:
        return None

    if not os.path.exists(file_path):
        logger.warning(f"Functions config file not found: {file_path}")
        return None

    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)

        if not isinstance(config, dict):
            logger.warning(f"Invalid functions config format in {file_path}: expected dict")
            return None

        return config
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse functions config {file_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error loading functions config {file_path}: {e}")
        return None


def load_packaged_functions():
    """Load the default packaged functions configuration.

    This loads config/functions.yaml, which must exist in the package.
    Failure to load is a fatal error — the config file is a required resource.

    Returns:
        dict: Functions configuration with 'functions' and 'metadata' keys

    Raises:
        RuntimeError: If packaged functions.yaml cannot be loaded
    """
    config = load_functions_config(str(PACKAGED_FUNCTIONS_PATH))
    if config is None:
        raise RuntimeError(
            f"Packaged functions.yaml not found or invalid: {PACKAGED_FUNCTIONS_PATH}\n"
            "This is a required resource. Ensure the package was installed correctly."
        )
    return config


def merge_user_functions(packaged_config, user_config, verbose=0):
    """Merge user functions config with packaged config.

    User functions override packaged functions with the same name.

    Args:
        packaged_config: dict with 'functions' key from packaged config
        user_config: dict with 'functions' key from user config
        verbose: verbosity level for warnings

    Returns:
        dict: Merged functions (user overrides packaged)
    """
    if not packaged_config or "functions" not in packaged_config:
        return user_config.get("functions", {}) if user_config else {}

    if not user_config or "functions" not in user_config:
        return packaged_config.get("functions", {})

    # Merge: start with packaged, override with user
    merged = dict(packaged_config.get("functions", {}))
    user_functions = user_config.get("functions", {})

    for func_name, func_def in user_functions.items():
        if func_name in merged and verbose >= 1:
            logger.info(f"User function {func_name} overrides packaged function")
        merged[func_name] = func_def

    return merged


def validate_function_definition(func_name, func_def, verbose=0):
    """Validate a function definition has required fields.

    Args:
        func_name: Name of the function (e.g., "$clog2")
        func_def: Function definition dict
        verbose: verbosity level for warnings

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(func_def, dict):
        if verbose >= 1:
            logger.warning(f"Function {func_name}: definition is not a dict")
        return False

    required_fields = ["python_func"]
    for field in required_fields:
        if field not in func_def:
            if verbose >= 1:
                logger.warning(f"Function {func_name}: missing required field '{field}'")
            return False

    return True


def evaluate_builtin_function(func_name, arg_str, functions_config, known_values=None, verbose=0):
    """Evaluate a SystemVerilog built-in function.

    Handles two types of function definitions:
    1. Inline expressions: python_func is Python code string, library specifies required imports
    2. Module functions: python_func is function name, library="sv_builtin_functions" imports module

    Gracefully handles errors: ZeroDivisionError, OverflowError, RecursionError, ValueError.
    On error, logs warning and returns None (treated as UNRESOLVED by caller).

    Args:
        func_name: Name of function including $ (e.g., "$clog2")
        arg_str: String representation of argument (e.g., "256" or "DEPTH")
        functions_config: dict mapping function names to definitions
        known_values: dict of parameter names to their values
        verbose: verbosity level (0=silent, 1=warn, 2=debug)

    Returns:
        int or None: Evaluated result, or None if evaluation fails or unresolvable
    """
    if not functions_config or func_name not in functions_config:
        if verbose >= 1:
            logger.warning(f"Unknown function: {func_name}")
        return None

    func_def = functions_config[func_name]

    if not validate_function_definition(func_name, func_def, verbose):
        return None

    # Try to resolve the argument
    arg_value = _resolve_argument(arg_str, known_values, verbose)
    if arg_value is None:
        if verbose >= 1:
            logger.warning(f"Could not resolve argument for {func_name}: {arg_str}")
        return None

    library = func_def.get("library", "builtin")
    python_func_ref = func_def.get("python_func", "")

    # Handle sv_builtin_functions module
    if library == "sv_builtin_functions":
        try:
            from rtl_aid import sv_builtin_functions
            if not hasattr(sv_builtin_functions, python_func_ref):
                if verbose >= 1:
                    logger.warning(f"{func_name}: function '{python_func_ref}' not found in sv_builtin_functions")
                return None

            func = getattr(sv_builtin_functions, python_func_ref)
            result = func(arg_value)

            if verbose >= 2:
                logger.debug(f"{func_name}({arg_str}) = {arg_value} → {result}")

            return result
        except ZeroDivisionError:
            if verbose >= 1:
                logger.warning(f"{func_name}({arg_str}): division by zero")
            return None
        except RecursionError:
            if verbose >= 1:
                logger.warning(f"{func_name}({arg_str}): recursion limit exceeded")
            return None
        except OverflowError:
            if verbose >= 1:
                logger.warning(f"{func_name}({arg_str}): numeric overflow")
            return None
        except (ValueError, TypeError) as e:
            if verbose >= 1:
                logger.warning(f"{func_name}({arg_str}): {e}")
            return None
        except Exception as e:
            if verbose >= 1:
                logger.warning(f"{func_name}({arg_str}): evaluation failed: {e}")
            return None

    # Handle inline expressions with library imports
    try:
        safe_dict = {
            "x": arg_value,
            "len": len,
            "isinstance": isinstance,
            "int": int,
            "str": str,
            "list": list,
            "tuple": tuple,
            "hasattr": hasattr,
            "max": max,
            "bin": bin,
        }

        # Import required library into safe namespace
        if library == "math":
            safe_dict["math"] = math
        elif library != "builtin":
            if verbose >= 2:
                logger.debug(f"{func_name}: library '{library}' not recognized, skipping import")

        result = eval(python_func_ref, {"__builtins__": {}}, safe_dict)

        if verbose >= 2:
            logger.debug(f"{func_name}({arg_str}) = {arg_value} → {result}")

        return result

    except ZeroDivisionError:
        if verbose >= 1:
            logger.warning(f"{func_name}({arg_str}): division by zero")
        return None
    except RecursionError:
        if verbose >= 1:
            logger.warning(f"{func_name}({arg_str}): recursion limit exceeded")
        return None
    except OverflowError:
        if verbose >= 1:
            logger.warning(f"{func_name}({arg_str}): numeric overflow")
        return None
    except (ValueError, TypeError) as e:
        if verbose >= 1:
            logger.warning(f"{func_name}({arg_str}): {e}")
        return None
    except Exception as e:
        if verbose >= 1:
            logger.warning(f"{func_name}({arg_str}): evaluation failed: {e}")
        return None


def _resolve_argument(arg_str, known_values=None, verbose=0):
    """Resolve an argument string to a value.

    Handles:
    - Integer literals: "256"
    - Parameter references: "DEPTH" (looks up in known_values)
    - Arithmetic expressions: "BASE * 2"
    - Nested functions: "$bits(...)" (recursively evaluated)

    Args:
        arg_str: String to resolve
        known_values: dict of parameter names to values
        verbose: verbosity level

    Returns:
        int or list or None: Resolved value
    """
    arg_str = arg_str.strip()
    known_values = known_values or {}

    # Try to parse as integer
    try:
        return int(arg_str)
    except ValueError:
        pass

    # Try parameter substitution
    if arg_str in known_values:
        val = known_values[arg_str]
        if isinstance(val, int):
            return val
        # If it's a list/array, return it for $size to use
        if isinstance(val, (list, tuple)):
            return val

    # Try arithmetic expression
    from rtl_aid.core import _safe_eval_int
    result = _safe_eval_int(arg_str)
    if result is not None:
        return result

    # Could not resolve
    return None


def extract_nested_functions(expr):
    """Extract nested function calls from an expression.

    Args:
        expr: Expression string (e.g., "$clog2($bits(16))")

    Returns:
        list: List of (func_name, args_str) tuples in bottom-up order
    """
    # Find all $func(...) patterns, innermost first
    pattern = r'\$(\w+)\s*\(([^)]*)\)'

    matches = []
    temp_expr = expr

    while True:
        # Find innermost function (no nested parens in args)
        match = re.search(r'\$(\w+)\s*\(([^$()]*)\)', temp_expr)
        if not match:
            break

        func_name = '$' + match.group(1)
        args = match.group(2).strip()
        matches.append((func_name, args))

        # Replace this function with a placeholder for next iteration
        temp_expr = temp_expr[:match.start()] + "X" + temp_expr[match.end():]

    return matches


def resolve_parameter_with_functions(expr, functions_config, known_values=None, verbose=0):
    """Resolve a parameter expression that may contain functions.

    Args:
        expr: Expression string (e.g., "$clog2(256)" or "$clog2(DEPTH * 2)")
        functions_config: dict of function definitions
        known_values: dict of parameter names to values
        verbose: verbosity level

    Returns:
        tuple: (resolved_value, display_string) where:
               - resolved_value is int or None
               - display_string is formatted representation
    """
    if not expr or not functions_config:
        return None, expr

    # Check if expression contains functions
    if '$' not in expr:
        # No functions, use existing parameter resolution
        from rtl_aid.core import _safe_eval_int
        result = _safe_eval_int(expr)
        return result, expr

    # Try to evaluate the entire expression with functions
    result = _evaluate_expr_with_functions(expr, functions_config, known_values, verbose)

    return result, expr


def _evaluate_expr_with_functions(expr, functions_config, known_values=None, verbose=0):
    """Evaluate an expression containing functions.

    Args:
        expr: Expression with functions (e.g., "$clog2(256)")
        functions_config: dict of function definitions
        known_values: dict of parameter names to values
        verbose: verbosity level

    Returns:
        int or None: Evaluated result
    """
    expr = expr.strip()
    known_values = known_values or {}

    # Extract nested functions bottom-up
    nested_funcs = extract_nested_functions(expr)

    if not nested_funcs:
        # No functions found, try arithmetic evaluation
        from rtl_aid.core import _safe_eval_int
        return _safe_eval_int(expr)

    # Evaluate functions bottom-up
    replacements = {}
    temp_expr = expr

    for func_name, args in nested_funcs:
        # Resolve the argument (may itself contain functions/parameters)
        arg_value = _resolve_argument(args, known_values, verbose)

        # Evaluate the function
        result = evaluate_builtin_function(func_name, args, functions_config, known_values, verbose)

        if result is None:
            # Function evaluation failed
            return None

        # Replace function with result for next iteration
        func_call = f"{func_name}({args})"
        temp_expr = temp_expr.replace(func_call, str(result), 1)
        replacements[func_call] = result

    # Now evaluate the final expression
    from rtl_aid.core import _safe_eval_int
    return _safe_eval_int(temp_expr)
