import html
import re
from typing import Any, Dict

from common_utils.logger import get_logger

logger = get_logger(__name__)


def replace_placeholders(text: str, attributes: Dict[str, Any]) -> str:
    if not text:
        return text

    attributes = attributes or {}
    placeholders_in_text = re.findall(r"\{([^}]+)\}", text)
    unresolved = [p for p in placeholders_in_text if p not in attributes]
    if unresolved:
        raise ValueError(f"Unresolved placeholders found: {unresolved}")

    for key, value in attributes.items():
        text = text.replace(f"{{{key}}}", str(value))

    return text


def replace_links(
    text: str, link_map: Dict[str, Any], link_placeholder_map: Dict[str, str]
) -> str:
    """
    Replace <LINK:PLACEHOLDER>label</LINK> with HTML <a> tags.
    """
    logger.debug(
        f"replace_links input - text: {text}, link_map: {link_map}, link_placeholder_map: {link_placeholder_map}"
    )

    if not link_map:
        logger.debug("replace_links - no link_map provided, returning original text")
        return text

    pattern = re.compile(r"<LINK:([A-Z0-9_-]+)>(.*?)</LINK>", re.IGNORECASE)
    matches = pattern.findall(text)
    logger.debug(f"replace_links - found {len(matches)} link matches: {matches}")

    def replacer(match):
        placeholder = match.group(1)
        label = html.escape(match.group(2))  # escape to be safe
        link_template = link_map.get(placeholder)
        logger.debug(
            f"replace_links - processing placeholder '{placeholder}' with label '{label}', link_template: {link_template}"
        )

        if not link_template:
            # fallback: just keep the label if no URL mapping
            logger.debug(
                f"replace_links - no URL found for placeholder '{placeholder}', returning label only"
            )
            return label

        try:
            link = replace_placeholders(link_template, link_placeholder_map)
            url = link
            logger.debug(
                f"replace_links - resolved URL for placeholder '{placeholder}': {url}"
            )
        except ValueError as e:
            # If placeholder resolution fails (e.g., unresolved placeholders),
            # log and fall back to using the template as-is or just the label
            logger.warning(
                f"replace_links - failed to resolve placeholders in link template for '{placeholder}': {e}. Using template as-is."
            )
            url = link_template

        if url:
            result = f'<a href="{url}">{label}</a>'
            logger.debug(f"replace_links - created link tag: {result}")
            return result
        else:
            # fallback: just keep the label if no URL mapping
            logger.debug(
                f"replace_links - no URL found for placeholder '{placeholder}', returning label only"
            )
            return label

    result = pattern.sub(replacer, text)
    logger.debug(f"replace_links output: {result}")
    return result
