# Frontend rules — Next.js 14 App Router

## Component conventions
- All components in src/components/ with PascalCase names
- Use server components by default, client only when needed
- No inline styles — Tailwind classes only
- Every component needs a TypeScript interface for its props

## State management
- Server state: React Query (TanStack Query)
- Client state: Zustand for global, useState for local
- Never use Redux

## API calls
- All API calls go through src/lib/api.ts
- Never fetch directly from components
- Always handle loading and error states
