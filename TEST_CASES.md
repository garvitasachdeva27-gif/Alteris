# Alteris Test Cases

| # | Test Case | Expected Result | Status |
|---|---|---|---|
| 1 | Health check endpoint responds | Returns `{"status": "ok"}` | Pass |
| 2 | Signup with valid email/password | Returns access token | Pass |
| 3 | Signup with duplicate email | Returns 400 error | Pass |
| 4 | Signup with malformed email | Returns 422 validation error | Pass |
| 5 | Login with correct credentials | Returns access token | Pass |
| 6 | Login with wrong password | Returns 401 error | Pass |
| 7 | Access protected route with no token | Returns 401 error | Pass |
| 8 | Access protected route with invalid/garbage token | Returns 401 error | Pass |
| 9 | Create and list a prompt | Prompt saved, list returns it with correct fields | Pass |
| 10 | Update a prompt (partial) | Only specified fields change, others preserved | Pass |
| 11 | Delete a prompt | Prompt removed, subsequent GET returns 404 | Pass |
| 12 | User A cannot read or delete User B's prompt by ID | Returns 404 (not 403, to avoid leaking existence); User A's copy is untouched | Pass |
| 13 | Prompt list is correctly scoped per user | Each user sees only their own prompts | Pass |
| 14 | Create a version snapshot and revert to it | Version number is 1; live prompt content matches after revert | Pass |
| 15 | Multiple versions increment sequentially | v1, v2 assigned in order | Pass |
| 16 | Missing/invalid required fields on create (email, prompt title/content) | Returns 422 validation error | Pass |

Run the full automated suite with: `pytest test_alteris.py -v` (16/16 passing).

## Testing Philosophy

These tests are risk-based rather than exhaustive: they cover the flows that
would be most damaging if they silently broke — especially ownership
isolation (test #13–15), since a failure there would mean one user's private
prompts leaking to another user. Each test uses an isolated `test_alteris.db`
that is wiped before every test function, so results are consistent and
never depend on what's already in the real development database.
