"""Clarification messages are built from validation results, not written by the LLM (D-004).

An LLM may later polish the wording, but the questions themselves come from here, so the customer
is asked for exactly what's missing.
"""

from app.schemas.pricing import Catalog
from app.services.validator import Issue, ValidatedItem, ValidationResult

SPEC_QUESTIONS = {
    "size_mix": "sizes and how many of each (e.g. M:10, L:15)",
    "print_type": "print type",
    "placement": "where the print goes (front, back, sleeve)",
    "color": "colour",
    "logo": "logo",
    "width_ft": "width in feet",
    "height_ft": "height in feet",
    "length_rft": "length in running feet",
    "design": "design (a photo or reference helps)",
    "finish": "finish",
    "glass": "glass",
    "shutter": "shutter type",
    "laminate": "laminate colour or code",
    "material": "material",
    "shutter_finish": "shutter finish",
}

GREETING = "Thanks! To prepare your quote I need a few more details:"
NO_ITEMS = "Thanks for reaching out! Which products would you like a quote for, and how many?"


def _readable(option: str) -> str:
    return option.replace("_", " ")


def _choices(options: list[str]) -> str:
    words = [_readable(o) for o in options]
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} or {words[-1]}"


def _question(issue: Issue, item: ValidatedItem, catalog: Catalog) -> str:
    catalog_item = catalog.get(item.sku) if item.sku else None
    unit = catalog_item.unit if catalog_item else None
    match issue.code:
        case "unmatched":
            return "we couldn't find this in our catalogue; could you describe it another way?"
        case "ambiguous":
            names = [c.name for sku in issue.options if (c := catalog.get(sku))]
            return f"which one do you mean: {_choices(names)}?"
        case "missing_quantity":
            return f"how many{f' {unit}' if unit else ''}?"
        case "below_moq":
            assert catalog_item is not None
            return f"our minimum is {catalog_item.moq} {catalog_item.unit}; is that okay?"
        case "missing_spec":
            question = SPEC_QUESTIONS.get(issue.field or "", _readable(issue.field or "details"))
            return f"{question} ({_choices(issue.options)})" if issue.options else question
        case "invalid_option":
            question = SPEC_QUESTIONS.get(issue.field or "", _readable(issue.field or ""))
            return f"{question}: please choose {_choices(issue.options)}"
        case _:
            return issue.message


def clarify_message(result: ValidationResult, catalog: Catalog) -> str:
    if result.complete:
        raise ValueError("nothing to clarify")
    if not result.items:
        return NO_ITEMS
    lines = [GREETING]
    for item in result.items:
        if item.complete:
            continue
        label = item.name or f'"{item.item_text}"'
        questions = "; ".join(_question(i, item, catalog) for i in item.issues)
        lines.append(f"- {label}: {questions}")
    return "\n".join(lines)
