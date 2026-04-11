---
globs: ["**/*.py"]
---
# Python rules (applies to all .py files)

- Type hints required on every function signature
- Docstrings required on every public function
- Use structlog for logging, never print()
- Raise specific exceptions, never bare Exception
- Use async/await for all I/O operations
