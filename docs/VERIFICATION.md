# Verification

Tested on **Apache Airflow 3.3.2**, Python 3.12, using the installed wheel outside the repository.

- **131 tests pass**, with no warnings or skipped tests.
- Airflow discovers the plugin through its package entry point.
- The registered DAG bundle supplies `retcon_apply` and `retcon_cascade` without import errors.
- `retcon configure` initializes a fresh Airflow config and is idempotent.
- The local demo opens without a login form.
- Model settings persist in an encrypted Airflow Connection.
- The full Gemma workflow completes asset scheduling, repair, native HITL approval, and publication.

The Aster demo checks **3 chapters**, repairs **2 paragraphs**, and leaves **3 chapters unchanged**. The published manuscript passes the implemented continuity rules.
