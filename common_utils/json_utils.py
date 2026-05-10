import re

from common_utils.logger import get_logger

logger = get_logger(__name__)


def replace_empty_dicts_with_none(obj) -> None:
    """
    Recursively replace any empty dictionary {} in the given object with None.
    """
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if isinstance(value, dict):
                if not value:  # Empty dict
                    obj[key] = None
                else:
                    replace_empty_dicts_with_none(value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        if not item:
                            obj[key][i] = None
                        else:
                            replace_empty_dicts_with_none(item)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, dict):
                if not item:
                    obj[i] = None
                else:
                    replace_empty_dicts_with_none(item)


def clean_json_response(content: str) -> str | None:
    """
    Clean JSON response by removing trailing commas and other common JSON formatting issues.

    Args:
        content: Raw JSON content that may contain formatting issues

    Returns:
        Cleaned JSON content
    """
    original_content = content

    # Remove markdown code block markers
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]  # Remove ```json
    elif content.startswith("```"):
        content = content[3:]  # Remove ```

    if content.endswith("```"):
        content = content[:-3]  # Remove trailing ```

    content = content.strip()

    # Remove trailing commas before closing braces and brackets
    # This regex matches commas that are followed by closing braces/brackets with optional whitespace
    # We need to handle nested objects, so we'll do this iteratively
    iterations = 0
    while True:
        new_content = re.sub(r",(\s*[}\]])", r"\1", content)
        if new_content == content:
            break
        content = new_content
        iterations += 1
        if iterations > 10:  # Safety check to prevent infinite loops
            logger.warning("JSON cleaning exceeded maximum iterations, stopping")
            break

    # Additional cleaning for other common JSON issues
    # Remove trailing commas followed by newlines and closing braces/brackets
    content = re.sub(r",\s*\n\s*([}\]])", r"\n\1", content)

    # Remove trailing commas in object properties
    content = re.sub(r",\s*([}\]])", r"\1", content)

    if content != original_content:
        logger.debug("JSON content was cleaned to fix formatting issues")

    return content
