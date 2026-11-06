---
type: data-model
title: User Model
description: The User POJO — its fields, validation constraints, active/inactive lifecycle states, ID assignment, and in-memory persistence characteristics.
tags: [model, user, validation, lifecycle, pojo]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-02T03:32:07.279Z
sources:
  - id: openwiki-source-285227629f0b88ea0e65b470
    resource: repo://src/main/java/com/example/userapi/model/User.java
  - id: openwiki-source-c7f84d3f13f5f73cca00d717
    resource: repo://src/main/java/com/example/userapi/service/UserService.java
generated: { by: "claude-code", at: "2026-11-02T03:32:07.279Z" }
---

# User Model

`User` (`src/main/java/com/example/userapi/model/User.java`) is a plain Java object (no JPA/ORM annotations). It is both the REST request/response body and the in-memory store value.

## Fields

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | `Long` | none (set by service) | Assigned by `UserService.createUser`; ignored on inbound POST |
| `username` | `String` | `@NotBlank` | Required; exact-match key for `getUserByUsername` |
| `email` | `String` | `@NotBlank`, `@Email` | Must be a well-formed email address |
| `fullName` | `String` | none | Optional display name |
| `createdAt` | `LocalDateTime` | none (set on construction) | Set to `LocalDateTime.now()` in both constructors; preserved across updates |
| `active` | `boolean` | none | Defaults to `true` in both constructors |

## Validation

Bean Validation constraints (`jakarta.validation`) are enforced when the controller receives a request body annotated with `@Valid`. Failures return `400 Bad Request` before the service is called. There is no server-side uniqueness check — duplicate usernames or emails are accepted silently.

## Active/inactive lifecycle

Users are never hard-deleted by the activate/deactivate endpoints. The `active` flag starts `true` and is toggled in place:

- `PATCH /{id}/deactivate` → `active = false`
- `PATCH /{id}/activate` → `active = true`
- `GET /active` filters to `active == true`
- `DELETE /{id}` is the only way to permanently remove a user

## ID assignment

`UserService` holds an `AtomicLong idGenerator` initialised to `1`. Every `createUser` call atomically increments it and sets `user.id` before inserting into the map. IDs are never reused — deleting a user does not reclaim its ID.

## Constructors

Two constructors exist:

```java
// No-arg: used by Jackson for deserialization
User()           // sets createdAt = now(), active = true

// Convenience constructor used for seeding
User(Long id, String username, String email, String fullName)
                 // sets createdAt = now(), active = true
                 // id is set here but overwritten by createUser()
```

The `id` passed to the convenience constructor is always overwritten by `UserService.createUser` before the record is stored, making the argument effectively unused.

## Persistence characteristics

`User` objects are stored directly in `ConcurrentHashMap<Long, User>`. There is no serialisation, no database, and no durability — all records are lost when the process stops. The three seed users (`admin`, `john_doe`, `jane_smith`) are recreated from the service constructor on every cold start.
