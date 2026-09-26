"""Narrow syntax rejection checks, never proof of mathematical fidelity."""
import re


def math_syntax_failure(latex):
    """Reject an operand-free grouped left side of an equation.

    This first check deliberately does not parse LaTeX, right-hand sides,
    function calls or equations whose left side was lost entirely. None means
    no defect established by this check, not that the expression is valid.
    """
    left, separator, _ = latex.partition('=')
    if (separator and '(' in left and
            re.fullmatch(r'[\s()+\-\u2212]+', left)):
        return 'equation_lhs_missing_operand'
    return None
