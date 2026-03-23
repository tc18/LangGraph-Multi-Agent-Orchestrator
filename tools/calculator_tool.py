from langchain.tools import tool


@tool
def calculator(expression: str) -> str:
    """
    Use this tool ONLY for math calculations.

    Input must be a valid Python expression.
    Examples:
    - 2+2
    - 5*3
    - 10/2

    Do NOT include quotes.
    Do NOT write calculator(...).
    Only pass raw expression.
    """
    print('-'*10)
    print(expression)
    try:
        expression = expression.replace("x", "*")
        return str(eval(expression))
    except Exception as e:
        return f"Error: {str(e)}"
