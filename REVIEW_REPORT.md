# Code Review Report — `main` (3 commits)

**Date**: 2026-04-17
**Branch**: `main`
**Commits reviewed**: 3
**Files reviewed**: 3
**Findings**: 0 CRITICAL, 3 WARNING, 2 SUGGESTION

---

## Findings

### src/audiobooks/research_papers/transcript_generator.py

**WARNING** Code Quality: Unused `client` parameter in `_generate_realtime`

The `client` parameter is passed from `generate()` but never used inside `_generate_realtime`. The method creates its own `genai.Client` instances per API-key tier. This makes the signature misleading and the caller allocates a client object for nothing.

- Current:
```python
def _generate_realtime(
    self, client: genai.Client, system_prompt: str, user_prompt: str
) -> str:
```
- Suggested:
```python
def _generate_realtime(
    self, system_prompt: str, user_prompt: str
) -> str:
```

Also update all call sites in `generate()` and `_generate_interrogator_episode()`:
```python
# In generate():
transcript = self._generate_realtime(system_prompt, prompt)

# In _generate_interrogator_episode():
result = self._generate_realtime(system_prompt, user_prompt)
```

And remove `client = genai.Client(api_key=self.api_key)` from `generate()` if it has no other uses.

- Rationale: Dead parameters confuse readers and create unnecessary object allocations. Removing the parameter makes the method's self-contained client management explicit.

---

### src/audiobooks/research_papers/transcript_generator.py

**WARNING** Code Quality: Redundant conditional in `_try_model` ClientError handler

Both branches of the `ClientError` handler do the same thing — `raise`. The `if/else` is dead logic.

- Current:
```python
except genai_errors.ClientError as e:
    # 429 quota exhausted — bubble up immediately for API key swap
    if getattr(e, "code", None) == 429:
        raise
    raise
```
- Suggested:
```python
except genai_errors.ClientError:
    raise
```

- Rationale: The identical branches make it look like the non-429 case was meant to have different handling (e.g., logging or wrapping). If all client errors should propagate, just re-raise unconditionally. If non-429 errors should be handled differently in the future, add a comment noting the intent.

---

### src/audiobooks/generate_audiobook.py

**WARNING** Code Quality: Inline import of `MIMEText` inside `send_notification_email`

- Current:
```python
def send_notification_email(service, date_str: str, expected_filename: str) -> None:
    ...
        from email.mime.text import MIMEText
        message = MIMEText(body)
```
- Suggested:
```python
# At the top of the file, with other imports:
from email.mime.text import MIMEText

# In the function body, remove the inline import:
        message = MIMEText(body)
```
- Rationale: PEP 8 recommends placing all imports at the top of the file. `email.mime.text` is a stdlib module with negligible import cost, so there is no performance justification for a lazy import.

---

### src/audiobooks/generate_audiobook.py

**SUGGESTION** Type Safety: Missing type hint for `service` parameter

- Current:
```python
def send_notification_email(service, date_str: str, expected_filename: str) -> None:
```
- Suggested:
```python
from googleapiclient.discovery import Resource

def send_notification_email(service: Resource, date_str: str, expected_filename: str) -> None:
```
- Rationale: All other parameters have type hints but `service` does not. Adding a type hint improves IDE autocompletion and documents the expected type for callers.

---

### src/audiobooks/generate_audiobook.py

**SUGGESTION** Type Safety: Missing type hint for `gmail_service` parameter

- Current:
```python
def request_user_feedback(date_str: str, gmail_service=None) -> str | None:
```
```python
def generate_and_upload_audio_hybrid(
    text_content: str, text_blocks: list, config: dict, date_str: str, gmail_service=None
) -> list:
```
- Suggested:
```python
def request_user_feedback(date_str: str, gmail_service: Resource | None = None) -> str | None:
```
```python
def generate_and_upload_audio_hybrid(
    text_content: str, text_blocks: list, config: dict, date_str: str, gmail_service: Resource | None = None
) -> list:
```
- Rationale: Consistent type hints across the new parameters improve readability and enable static analysis.

---

## Files With No Findings

- `src/audiobooks/research_papers/run_research_pipeline.py` — Clean config passthrough with safe `fallback=None` defaults. No issues.

---

## Top 3 Most Impactful Improvements

1. **Remove unused `client` parameter from `_generate_realtime`** — Eliminates a misleading API and unnecessary object allocation on every call.
2. **Simplify redundant ClientError handler in `_try_model`** — Removes dead conditional logic that suggests incomplete handling.
3. **Move `MIMEText` import to top of file** — Aligns with PEP 8 import conventions for standard library modules.
