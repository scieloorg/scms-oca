import re


INT_RE = re.compile(r"^[+-]?\d+$")
FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?$")


def safe_int(value: str | int | float | None) -> int | None:
    """Convert a value to integer safely, handling strings and floats."""
    if value is None:
        return None
    
    text = str(value).strip()
    if not text:
        return None
    
    if INT_RE.match(text):
        return int(text)
    
    if FLOAT_RE.match(text):
        try:
            return int(float(text))
        except (ValueError, TypeError):
            return None
            
    return None


def safe_float(value: str | int | float | None) -> float | None:
    """Convert a value to float safely."""
    if value is None:
        return None
        
    text = str(value).strip()
    if not text:
        return None
        
    if FLOAT_RE.match(text):
        try:
            return float(text)
        except (ValueError, TypeError):
            return None
            
    return None
