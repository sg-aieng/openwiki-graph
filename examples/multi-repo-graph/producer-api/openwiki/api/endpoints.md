---
type: api-reference
title: User API Endpoints
description: All REST endpoints exposed under /api/users — HTTP methods, paths, request bodies, response shapes, status codes, and validation constraints.
tags: [rest, api, users, endpoints, crud]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-02T03:32:07.279Z
sources:
  - id: openwiki-source-513bde25c0e66ae5c122cef9
    resource: repo://src/main/java/com/example/userapi/controller/UserController.java
  - id: openwiki-source-285227629f0b88ea0e65b470
    resource: repo://src/main/java/com/example/userapi/model/User.java
  - id: openwiki-source-c7f84d3f13f5f73cca00d717
    resource: repo://src/main/java/com/example/userapi/service/UserService.java
  - id: openwiki-source-ece093ad10b91f3da0b7e34f
    resource: repo://src/main/resources/application.properties
generated: { by: "claude-code", at: "2026-11-02T03:32:07.279Z" }
---

# User API Endpoints

All endpoints share the base path `/api/users`. The server runs on port `8080` by default (`server.port` in `application.properties`).

## Endpoints

### List all users

```
GET /api/users
```

Returns all users regardless of active status.

**Response:** `200 OK` — array of [User](#user-response-shape) objects.

---

### List active users

```
GET /api/users/active
```

Returns only users whose `active` flag is `true`.

**Response:** `200 OK` — filtered array of User objects.

---

### Get user by ID

```
GET /api/users/{id}
```

**Response:**
- `200 OK` — User object
- `404 Not Found` — no user with that ID

---

### Get user by username

```
GET /api/users/username/{username}
```

Exact-match lookup by username (case-sensitive).

**Response:**
- `200 OK` — User object
- `404 Not Found` — no user with that username

---

### Create user

```
POST /api/users
Content-Type: application/json
```

**Request body:**

```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "fullName": "New User"
}
```

Validation constraints (applied via `@Valid`):
- `username` — required, non-blank
- `email` — required, must be a well-formed email address
- `fullName` — optional

**Response:**
- `201 Created` — the created User (with assigned `id` and `createdAt`)
- `400 Bad Request` — validation failure

---

### Update user

```
PUT /api/users/{id}
Content-Type: application/json
```

Full replacement: all writable fields must be provided. `id` and `createdAt` are preserved from the existing record regardless of what the body contains.

**Response:**
- `200 OK` — updated User
- `404 Not Found` — no user with that ID

---

### Delete user

```
DELETE /api/users/{id}
```

Permanently removes the user from the in-memory store.

**Response:**
- `204 No Content` — deleted
- `404 Not Found` — no user with that ID

---

### Deactivate user

```
PATCH /api/users/{id}/deactivate
```

Sets `active = false` without removing the record.

**Response:**
- `200 OK` — deactivated
- `404 Not Found` — no user with that ID

---

### Activate user

```
PATCH /api/users/{id}/activate
```

Sets `active = true`.

**Response:**
- `200 OK` — activated
- `404 Not Found` — no user with that ID

---

## User response shape

```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "fullName": "Administrator",
  "createdAt": "2024-01-15T10:30:00",
  "active": true
}
```

`id` is a monotonically increasing `Long` assigned by `UserService`. `createdAt` is set to the instant the `User` object is constructed (before it reaches the service).
