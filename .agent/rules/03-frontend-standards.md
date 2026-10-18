# Regla 03: Estándares Frontend (React 19, TypeScript Strict, TanStack Query v5)
- `noImplicitAny: true`, `strictNullChecks: true` y `0` código muerto en `pnpm dlx knip`.
- Estado del servidor gestionado con TanStack React Query v5 y claves centralizadas en `queryKeys.ts`.
- Formularios con React Hook Form + Zod y aislamiento entre `features/` verificado por `.dependency-cruiser.cjs`.
