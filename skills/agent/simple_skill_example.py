"""
Simple Agent Skill Example - Auto-wrapped Format

This demonstrates the simplest way to create an agent skill.
Just define SKILL_INFO and an execute() function.

No class inheritance needed!
"""

# Skill metadata - required for auto-detection
SKILL_INFO = {
    "name": "simple_example",
    "description": "A simple example skill that echoes input",
    "version": "1.0.0",
    "author": "CursorBot",
    "parameters": {
        "message": "The message to process",
        "uppercase": "Convert to uppercase (true/false)",
    },
    "examples": [
        "Echo hello world",
        "Process my text",
    ],
    "categories": ["example", "text"],
}


# Execute function - can be sync or async
async def execute(message: str = "", uppercase: str = "false", **kwargs) -> dict:
    """
    Main execution function.
    
    Args:
        message: The message to process
        uppercase: Whether to convert to uppercase
        **kwargs: Additional arguments
    
    Returns:
        dict with results
    """
    if not message:
        return {"error": "No message provided"}
    
    result = message
    if uppercase.lower() == "true":
        result = result.upper()
    
    return {
        "status": "success",
        "original": message,
        "processed": result,
        "length": len(result),
    }


# Alternative function names also work: run() or main()
# async def run(**kwargs) -> dict:
#     ...
# async def main(**kwargs) -> dict:
#     ...
