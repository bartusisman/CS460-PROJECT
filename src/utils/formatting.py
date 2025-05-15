import re

def format_page_source(page_source, max_length=8000):
    """Format and truncate page source if needed"""
    if len(page_source) > max_length:
        # Simple truncation, could be improved with more intelligent parsing
        return page_source[:max_length] + "... (truncated)"
    return page_source

def split_navigation_steps(instruction):
    """Split a multi-step navigation instruction into individual steps"""
    # Common separation indicators
    separators = [
        " then ", " and then ", " after that ", " next ",
        ", then ", ", and then ", ", after that ", ", next ",
        "; then ", "; and then ", "; after that ", "; next ",
        " and "
    ]
    
    # Split by each separator
    steps = [instruction]
    for separator in separators:
        new_steps = []
        for step in steps:
            new_steps.extend(step.split(separator))
        steps = new_steps
    
    # Filter out empty steps and strip leading/trailing whitespace
    steps = [step.strip() for step in steps if step.strip()]
    
    # If no steps were found or no separators detected, return the original instruction
    if not steps:
        return [instruction]
    
    return steps

def execute_safely(command_func, *args, max_retries=3, retry_delay=2, **kwargs):
    """
    Execute a command with retry logic
    
    Args:
        command_func: Function to execute
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries (seconds)
        **kwargs: Keyword arguments to pass to the function
    
    Returns:
        The result of the function call, or None if all attempts fail
    """
    for attempt in range(max_retries):
        try:
            result = command_func(*args, **kwargs)
            return result
        except Exception as e:
            print(f"Command execution failed (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
    
    print("Failed to execute command after all retry attempts")
    return None 