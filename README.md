# Project README

## Overview

This repository is being migrated from Flask to FastAPI using an incremental, behavior-preserving approach.

The guiding principle is simple:

- **Keep the current application working** while migration happens.
- **Prove parity before cutting over** any route.
- **Preserve the existing database schema** until the new stack has demonstrated equivalent behavior.
- **Migrate slice by slice**, not by rewriting everything at once.

## Migration Strategy

The migration is organized into four phases:

1. **Golden-master contract tests**
2. **Dependency upgrade**
3. **Parity API layer**
4. **Slice-by-slice route cutover**

Each phase is designed to reduce risk and make regressions detectable early.

---

## 1) Golden-Master Contract Tests

Before changing application behavior, capture the current Flask behavior with contract tests.

### Goals

- Lock down existing request/response semantics.
- Document status codes, headers, payload shapes, and error responses.
- Preserve behavior for all critical routes before refactoring.

### What to cover

- Successful responses
- Validation failures
- Authentication/authorization flows
- Redirect behavior, if any
- Error payload formats
- Response headers that clients depend on
- Edge cases and known quirks in current behavior

### Guidance

- Treat the current Flask implementation as the **golden master**.
- Add tests around real application behavior, not just isolated helpers.
- Prefer black-box tests that exercise the public HTTP interface.

These tests become the safety net for every later migration step.

---

## 2) Dependency Upgrade

Once the golden-master tests are in place, upgrade dependencies in a controlled way.

### Goals

- Bring packages to versions compatible with the future FastAPI stack.
- Minimize breakage by upgrading incrementally.
- Keep the current Flask app stable while preparing for shared abstractions.

### Guidance

- Upgrade one dependency group at a time when possible.
- Run the golden-master tests after each change.
- Avoid broad refactors during dependency upgrades unless necessary for compatibility.
- Preserve the current runtime behavior and database schema.

This phase should not change public API behavior.

---

## 3) Parity API Layer

Introduce a FastAPI-based parity layer that mirrors the current Flask endpoints.

### Goals

- Implement FastAPI routes that match existing Flask behavior.
- Keep request/response contracts identical.
- Create a path for routing traffic to FastAPI handlers without changing observable behavior.

### Design Principles

- Reuse existing business logic whenever possible.
- Centralize shared domain/service code so both frameworks call the same implementation.
- Keep serialization, validation, and error handling aligned with the golden-master contracts.
- Ensure FastAPI endpoints produce the same outputs as Flask for the same inputs.

### Validation

- Run contract tests against both implementations.
- Compare responses for parity.
- Investigate and fix any mismatches before moving forward.

The parity layer should be treated as a compatibility bridge, not a redesign.

---

## 4) Slice-by-Slice Route Cutover

After parity is proven, migrate routes one slice at a time.

### Goals

- Move traffic from Flask to FastAPI gradually.
- Maintain stable behavior during each cutover.
- Roll back easily if parity breaks.

### Suggested approach

1. Choose a small route group or feature slice.
2. Verify the FastAPI implementation matches the golden-master contract.
3. Switch that slice from Flask to FastAPI.
4. Run the full test suite and observe production behavior.
5. Repeat for the next slice.

### Important constraints

- **Do not change the database schema during route cutover** unless a schema change is strictly required and separately validated.
- Preserve existing migrations and model assumptions until the FastAPI path has fully matched behavior.
- Keep shared business logic stable so both stacks remain consistent during transition.

This gradual cutover reduces risk and makes each migration step reversible.

---

## Behavior Preservation Rules

Throughout the migration, the following rules apply:

- Preserve current API behavior unless a deliberate, tested change is approved.
- Preserve status codes, headers, and payload formats.
- Preserve the database schema until parity is proven.
- Use tests to validate every visible behavior change.
- Prefer additive changes over breaking changes.

If a behavior change is required, it should be made intentionally, documented, and covered by tests.

---

## Recommended Execution Order

A practical execution order is:

1. Build golden-master contract tests for current Flask routes.
2. Upgrade dependencies with tests guarding behavior.
3. Add the FastAPI parity layer alongside Flask.
4. Compare outputs and close parity gaps.
5. Cut over routes slice by slice.
6. Keep the schema unchanged until the migration is complete and parity is stable.

---

## Definition of Done for a Slice

A route slice is considered migrated when:

- Golden-master tests pass against the FastAPI implementation.
- The slice behaves identically to the Flask version for supported inputs.
- No unintended schema changes were introduced.
- The cutover is stable in test and production environments.

---

## Notes

This README describes the migration approach only. For implementation details, follow the repository’s test, deployment, and release conventions.
