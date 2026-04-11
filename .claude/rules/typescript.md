---
globs: ["**/*.ts", "**/*.tsx"]
---
# TypeScript rules (applies to all .ts and .tsx files)

- Strict mode always on
- No any types — use unknown and narrow if needed
- Export types alongside their implementations
- Use const assertions for literal types
- Prefer type over interface for simple shapes
