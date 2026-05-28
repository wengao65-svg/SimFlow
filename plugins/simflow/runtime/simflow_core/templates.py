"""Simple Jinja2-compatible template renderer for SimFlow input files.

Supports:
- {{ variable | default(value) }}
- {% if condition %} ... {% elif %} ... {% else %} ... {% endif %}
- {% for item in iterable %} ... {% endfor %}

Does not require Jinja2 dependency.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


def render_template(template_path: str, variables: Dict[str, Any]) -> str:
    """Render a template file with the given variables.

    Args:
        template_path: Path to template file (absolute or relative to templates/)
        variables: Dict of variable name -> value

    Returns:
        Rendered string
    """
    if os.path.isabs(template_path):
        with open(template_path, "r") as f:
            template = f.read()
    else:
        full_path = TEMPLATES_DIR / template_path
        with open(full_path, "r") as f:
            template = f.read()

    return render_string(template, variables)


def render_string(template: str, variables: Dict[str, Any]) -> str:
    """Render a template string with the given variables.

    Args:
        template: Template string
        variables: Dict of variable name -> value

    Returns:
        Rendered string
    """
    # Process {% for %} loops first
    template = _process_for_loops(template, variables)
    # Process {% if %} blocks
    template = _process_if_blocks(template, variables)
    # Process {{ variable | default(value) }} substitutions
    template = _process_variables(template, variables)
    return template


def _process_variables(template: str, variables: Dict[str, Any]) -> str:
    """Replace {{ variable | default(value) }} patterns."""
    def replace_var(match):
        expr = match.group(1).strip()
        parts = expr.split("|")
        var_name = parts[0].strip()
        default_val = None

        for part in parts[1:]:
            part = part.strip()
            if part.startswith("default(") and part.endswith(")"):
                default_str = part[8:-1].strip().strip('"').strip("'")
                default_val = _parse_value(default_str)

        value = variables.get(var_name, default_val)
        if value is None:
            return match.group(0)  # Leave unresolved
        return str(value)

    return re.sub(r'\{\{(.+?)\}\}', replace_var, template)


def _process_if_blocks(template: str, variables: Dict[str, Any]) -> str:
    """Process {% if %} ... {% elif %} ... {% else %} ... {% endif %} blocks."""
    max_depth = 30
    for _ in range(max_depth):
        # Find innermost if block (no nested if inside)
        # Use a greedy approach: find the first {% if %} and its matching {% endif %}
        start_match = re.search(r'\{%\s*if\s+(.+?)\s*%\}', template)
        if not start_match:
            break

        # Find matching endif by counting nesting depth
        depth = 1
        pos = start_match.end()
        while depth > 0 and pos < len(template):
            next_if = re.search(r'\{%\s*if\s+', template[pos:])
            next_endif = re.search(r'\{%\s*endif\s*%\}', template[pos:])
            if next_endif is None:
                break
            if next_if and start_match.end() + next_if.start() < pos + next_endif.start():
                depth += 1
                pos += next_if.end()
            else:
                depth -= 1
                if depth == 0:
                    end_pos = pos + next_endif.end()
                    break
                pos += next_endif.end()
        else:
            break

        block = template[start_match.start():end_pos]
        condition_expr = start_match.group(1).strip()
        body = block[start_match.end() - start_match.start():]
        body = body[:-(len("{% endif %}"))]  # Remove trailing endif

        # Check for elif/else
        elif_else = re.split(r'\{%\s*elif\s+(.+?)\s*%\}', body)
        branches = [(condition_expr, elif_else[0])]

        i = 1
        while i < len(elif_else) - 1:
            branches.append((elif_else[i], elif_else[i + 1]))
            i += 2

        # Check for else
        last_body = branches[-1][1]
        else_split = re.split(r'\{%\s*else\s*%\}', last_body, maxsplit=1)
        if len(else_split) == 2:
            branches[-1] = (branches[-1][0], else_split[0])
            branches.append(("True", else_split[1]))

        # Evaluate branches
        result = ""
        for cond, body_text in branches:
            if _evaluate_condition(cond, variables):
                result = body_text
                break

        template = template[:start_match.start()] + result + template[end_pos:]

    return template


def _process_for_loops(template: str, variables: Dict[str, Any]) -> str:
    """Process {% for item in iterable %} ... {% endfor %} blocks."""
    max_depth = 10
    for _ in range(max_depth):
        match = re.search(
            r'\{%\s*for\s+(\w+)\s+in\s+(.+?)\s*%\}(.*?)\{%\s*endfor\s*%\}',
            template, re.DOTALL
        )
        if not match:
            break

        var_name = match.group(1)
        iterable_expr = match.group(2).strip()
        body = match.group(3)

        # Handle "var | default([...])" pattern
        if "|" in iterable_expr:
            parts = iterable_expr.split("|")
            iterable_name = parts[0].strip()
            default_val = None
            for part in parts[1:]:
                part = part.strip()
                if part.startswith("default(") and part.endswith(")"):
                    default_str = part[8:-1].strip()
                    default_val = _parse_value(default_str)
            iterable = variables.get(iterable_name, default_val or [])
        else:
            iterable = variables.get(iterable_expr, [])

        result_parts = []
        for item in iterable:
            item_vars = dict(variables)
            item_vars[var_name] = item
            result_parts.append(_process_variables(body, item_vars))

        template = template[:match.start()] + "".join(result_parts) + template[match.end():]

    return template


def _evaluate_condition(expr: str, variables: Dict[str, Any]) -> bool:
    """Evaluate a simple condition expression."""
    expr = expr.strip()

    # Handle "not" prefix
    if expr.startswith("not "):
        return not _evaluate_condition(expr[4:], variables)

    # Handle "or"
    if " or " in expr:
        parts = expr.split(" or ", 1)
        return _evaluate_condition(parts[0], variables) or _evaluate_condition(parts[1], variables)

    # Handle "and"
    if " and " in expr:
        parts = expr.split(" and ", 1)
        return _evaluate_condition(parts[0], variables) and _evaluate_condition(parts[1], variables)

    # Handle comparison operators
    for op in ["==", "!=", ">=", "<=", ">", "<"]:
        if op in expr:
            left, right = expr.split(op, 1)
            left_val = _resolve_value(left.strip(), variables)
            right_val = _resolve_value(right.strip(), variables)
            try:
                if op == "==":
                    return left_val == right_val
                elif op == "!=":
                    return left_val != right_val
                elif op == ">=":
                    return float(left_val) >= float(right_val)
                elif op == "<=":
                    return float(left_val) <= float(right_val)
                elif op == ">":
                    return float(left_val) > float(right_val)
                elif op == "<":
                    return float(left_val) < float(right_val)
            except (ValueError, TypeError):
                return False

    # Boolean literals
    if expr.lower() in ("true", ".true."):
        return True
    if expr.lower() in ("false", ".false."):
        return False

    # Simple truthy check - missing variables are falsy
    val = variables.get(expr)
    if val is None:
        return False
    return bool(val)


def _resolve_value(expr: str, variables: Dict[str, Any]) -> Any:
    """Resolve a value from expression or variable name."""
    expr = expr.strip()
    # String literal
    if (expr.startswith('"') and expr.endswith('"')) or \
       (expr.startswith("'") and expr.endswith("'")):
        return expr[1:-1]
    # Number
    try:
        return int(expr)
    except ValueError:
        try:
            return float(expr)
        except ValueError:
            pass
    # Boolean
    if expr.lower() in ("true", ".true."):
        return True
    if expr.lower() in ("false", ".false."):
        return False
    # Variable lookup
    return variables.get(expr, expr)


def _parse_value(s: str) -> Any:
    """Parse a string value to appropriate Python type."""
    if s.lower() in ("true", ".true."):
        return True
    if s.lower() in ("false", ".false."):
        return False
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def load_template(software: str, template_name: str) -> str:
    """Load a template by software and name.

    Args:
        software: Software name (vasp, qe, lammps, gaussian)
        template_name: Template file name (e.g., INCAR.template)

    Returns:
        Template string
    """
    path = TEMPLATES_DIR / software / template_name
    with open(path, "r") as f:
        return f.read()


def render_software_template(software: str, template_name: str, variables: Dict[str, Any]) -> str:
    """Load and render a software template.

    Args:
        software: Software name (vasp, qe, lammps, gaussian)
        template_name: Template file name
        variables: Template variables

    Returns:
        Rendered string
    """
    template = load_template(software, template_name)
    return render_string(template, variables)


def render_to_file(software: str, template_name: str, variables: Dict[str, Any],
                    output_path: str) -> str:
    """Render a template and write to file.

    Args:
        software: Software name
        template_name: Template file name
        variables: Template variables
        output_path: Output file path

    Returns:
        Output file path
    """
    content = render_software_template(software, template_name, variables)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)
    return output_path
