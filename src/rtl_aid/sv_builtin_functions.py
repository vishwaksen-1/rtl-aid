"""
SystemVerilog built-in functions requiring special logic beyond simple expressions.

These functions need context or multi-line validation that can't be expressed as
inline Python in the YAML config. They're called during parameter evaluation.
"""


def low(x):
    """Lowest legal index of array or vector.

    Requires array declaration context to determine if ascending or descending.
    Without context, cannot reliably determine the correct value.

    Args:
        x: Value (array size or index)

    Returns:
        int: 0 (conservative default for ascending arrays [0:N-1])
        None: If cannot determine (should use UNRESOLVED in caller)
    """
    return 0


def dimensions(x):
    """Number of dimensions of an array.

    Requires full declaration context to determine actual dimensions.
    A single value cannot tell if an array is 1D or multidimensional.

    Args:
        x: Value (ignored; cannot determine from value alone)

    Returns:
        int: 1 (conservative default; cannot detect multidimensional)
        None: If cannot determine (should use UNRESOLVED in caller)
    """
    return 1


def increment(x):
    """Array index increment direction: +1 (ascending) or -1 (descending).

    Requires array declaration to determine direction.
    [0:N-1] increments by +1, [N-1:0] increments by -1.

    Args:
        x: Value (ignored; cannot determine from value alone)

    Returns:
        int: 1 (conservative default for ascending arrays)
        None: If cannot determine (should use UNRESOLVED in caller)
    """
    return 1


def isunbounded(x):
    """Check if array is unbounded (dynamic, size not fixed).

    Requires declaration syntax (e.g., 'bit []' vs 'bit [7:0]') to determine.
    Cannot infer from value alone.

    Args:
        x: Value (ignored; cannot determine from value alone)

    Returns:
        int: 0 (False, conservative default)
        None: If cannot determine (should use UNRESOLVED in caller)
    """
    return 0
