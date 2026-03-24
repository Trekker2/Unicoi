# Code Style Guide & Linting Rules

> A comprehensive guide to maintain clean, consistent, and readable Python code.

---

## 1. File Structure & Organization

### File Header
Every Python file must begin with a structured docstring:

```python
"""
Module Name - Brief Description

A longer description explaining what this module does.

Key Functions:
    - function_name: Brief description
"""
```

### File Footer
Every Python file must end with:

```python
# END
```

(with exactly one blank line before it)

### Requirements File Organization
Libraries in `requirements.txt` should be organized alphabetically.

### File Length Limit
Try to keep Python files under 2,200 lines.

---

## 2. Imports & Dependencies

### Import Order
Imports ordered alphabetically within groups:

1. Standard library
2. Third-party libraries
3. Local modules

Each group separated by one blank line.

### Aliases
```python
import datetime as dt
import numpy as np
import pandas as pd
```

### Unused Imports
Do not import unused libraries.

---

## 3. Naming Conventions

- `snake_case` → variables, functions
- `PascalCase` → classes
- `UPPER_CASE` → constants

Never call a function `main()` unless inside `main.py`.

---

## 4. Functions & Return Statements

- Return early when possible
- Avoid deep nesting
- Use default parameters

---

## 5. Data Structures & Operations

- Use `.get()` for dictionary access with defaults
- Use list comprehensions when readable
- Prefer `enumerate()` over manual index tracking

---

## 6. String Formatting

- Use f-strings for interpolation
- Use double quotes for strings

---

## 7. Code Formatting & Whitespace

- 4-space indentation
- Blank lines between logical sections
- Max line length: 120 characters

---

## 8. Best Practices

- Functional style preferred (no classes unless necessary)
- Pattern-matching callbacks for dynamic UI
- Always handle API errors gracefully

---

## 9. Code Cleanliness

- Remove unused variables and imports
- Clean up temporary debug prints

---

## 10. Library Preferences

- Flask-Login for authentication
- pymongo for MongoDB
- exchange_calendars for market schedules
- bcrypt for password hashing

---

## 11. Documentation & GitHub Workflow

- Meaningful commit messages
- README with setup instructions
