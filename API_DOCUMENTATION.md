# Alteris API Documentation

Base URL (local): `http://127.0.0.1:8000`
Base URL (deployed): _your Render backend URL_

All protected routes require a header: `Authorization: Bearer <token>`

## Authentication

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/auth/signup` | Create a new account, returns a JWT | No |
| POST | `/auth/login` | Log in, returns a JWT | No |

**Signup/Login request body:**
```json
{ "email": "user@example.com", "password": "yourpassword" }
```
**Response:**
```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

## Prompts

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/prompts` | Create a new prompt | Yes |
| GET | `/prompts` | List all of your prompts | Yes |
| GET | `/prompts/{id}` | Get a single prompt | Yes |
| PUT | `/prompts/{id}` | Update a prompt (partial updates supported) | Yes |
| DELETE | `/prompts/{id}` | Delete a prompt | Yes |

## Execution

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/prompts/{id}/execute` | Run a prompt against Groq, logs the result | Yes |
| GET | `/prompts/{id}/history` | Get all past executions for a prompt | Yes |

**Execute request body:**
```json
{ "test_input": "A message to test the prompt with", "model": "llama-3.1-8b-instant" }
```

## Versions

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/prompts/{id}/versions` | Snapshot the current prompt as a new version | Yes |
| GET | `/prompts/{id}/versions` | List all saved versions | Yes |
| POST | `/prompts/{id}/versions/{version_id}/revert` | Revert live prompt to a saved version | Yes |

## A/B Testing

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | `/prompts/{id}/compare` | Run two versions against the same input concurrently | Yes |

**Compare request body:**
```json
{
  "test_input": "Same input sent to both versions",
  "version_a_id": null,
  "version_b_id": 3,
  "model": "llama-3.1-8b-instant"
}
```
`null` for either version ID means "use the current live prompt."

## Analytics

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| GET | `/prompts/{id}/analytics` | Per-prompt run count, avg tokens, avg latency | Yes |
| GET | `/insights` | Global stats, cost-over-time, category token usage | Yes |

## Error Responses

All errors follow FastAPI's standard shape:
```json
{ "detail": "Human-readable error message" }
```

| Status | Meaning |
|---|---|
| 401 | Missing or invalid auth token |
| 404 | Resource not found (or belongs to another user) |
| 422 | Request body failed validation |
| 502 | Upstream Groq API error |
