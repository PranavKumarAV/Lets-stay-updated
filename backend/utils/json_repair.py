"""
Unified JSON repair helpers.

This module provides a thin wrapper around the external `json-repair` package
for repairing invalid JSON emitted by language models.  If the external
library is available, its robust repair functions are used.  Otherwise, a
minimal fallback implementation is provided that performs basic cleanup such
as converting single quotes to double quotes and removing trailing commas.

The exposed functions mirror the API of the `json_repair` module on PyPI:

* ``jsonrepair(text: str) -> str``: return a repaired JSON string.
* ``loads(text: str) -> Any``: repair and decode a JSON-like string.
* ``dumps(obj) -> str``: encode a Python object to JSON.  This simply
  delegates to the standard library when the external package is not
  installed, since `json_repair` does not implement ``dumps`` itself.

Downstream code can import ``json_repair`` and access these helpers without
needing to directly depend on the external library.  When the external
package is present in the environment (as specified in
``backend/requirements.txt``), it will be used preferentially; otherwise, the
fallback routines ensure graceful degradation.
"""

from typing import Any

try:
    # Prefer the robust external implementation if installed.  The
    # json-repair package exposes a ``repair_json`` function and a ``loads``
    # function that behave similarly to json.loads but tolerate malformed
    # input.  We alias them here for clarity.  Note: the package name
    # includes a hyphen on PyPI but the import is ``json_repair``.
    import json_repair as _jr  # type: ignore
    import json as _json

    def jsonrepair(text: str) -> str:
        """Repair a JSON-like string using the external `json_repair` package.

        :param text: Raw JSON-like string that may contain syntax errors.
        :returns: Repaired JSON string.
        """
        if not isinstance(text, str):
            return text  # type: ignore[return-value]
        # ``repair_json`` returns a JSON string by default when ``return_objects``
        # is False.  If the string cannot be repaired it returns an empty
        # string, which will cause ``loads`` below to raise ``JSONDecodeError``.
        return _jr.repair_json(text)  # type: ignore[no-any-return]

    def loads(text: str) -> Any:
        """Repair and decode a JSON-like string using `json_repair`.

        :param text: Possibly malformed JSON string.
        :returns: Decoded Python object.
        """
        return _jr.loads(text)  # type: ignore[no-any-return]

    def dumps(obj: Any) -> str:
        """Serialize a Python object to a JSON string.

        The external library does not provide a ``dumps`` function, so we
        delegate to the built-in ``json.dumps``.
        """
        return _json.dumps(obj)

except ImportError:
    # Fallback minimal implementation when the external library is unavailable.
    import re
    import json as _json

    def jsonrepair(text: str) -> str:
        """Basic JSON repair fallback.

        Performs simple fixes such as replacing single quotes with double quotes
        and removing trailing commas before closing braces or brackets.
        """
        if not isinstance(text, str):
            return text  # type: ignore[return-value]
        repaired = text
        # Replace single quotes with double quotes
        repaired = repaired.replace("'", '"')
        # Remove trailing commas before closing braces/brackets
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        return repaired

    def loads(text: str) -> Any:
        """Repair a JSON-like string and decode it to a Python object.

        Strips extraneous characters outside the outermost braces, applies
        minimal repairs and then delegates to ``json.loads``.
        """
        if not isinstance(text, str):
            return text
        raw = text.strip()
        # Find the bounds of the JSON object
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1 and start < end:
            raw = raw[start:end + 1]
        repaired = jsonrepair(raw)
        return _json.loads(repaired)

    def dumps(obj: Any) -> str:
        """Serialize a Python object to a JSON string using the stdlib."""
        return _json.dumps(obj)