---
type: integration contract
title: User API Contract
description: Outbound HTTP contract used by the consumer to call the external User API, including the configured base URL, supported verbs, and where response-shape assumptions are made.
tags: [integration, http-client, consumer, user-api]
verified:
  - by: openwiki/0.7.3
    at: 2026-11-04T17:34:57.507Z
sources:
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-b6997fdb3ca346a82e33e462
    resource: repo://src/main/java/com/example/consumer/client/UserApiClient.java
  - id: openwiki-source-ece093ad10b91f3da0b7e34f
    resource: repo://src/main/resources/application.properties
generated: { by: "openwiki/0.7.3", at: "2026-11-04T17:34:57.507Z" }
---

# User API Contract

This consumer is a thin outbound client for the external User API producer. It does not own the server-side user lifecycle; instead, it reads the base URL from configuration and issues HTTP requests through `UserApiClient`.

<!-- openwiki: broken internal link [../src/main/resources/application.properties] file "../src/main/resources/application.properties" does not exist. Fix the href or restore the target, then delete this comment. -->
The runtime dependency is configured with `user.api.base-url`, which defaults to `http://localhost:8080` in [`application.properties`](../src/main/resources/application.properties). The README describes the same producer location as a prerequisite for running the demo consumer.

## Outbound endpoint matrix

| Operation | Method | Path | Client return type | Notes |
| --- | --- | --- | --- | --- |
| List all users | `GET` | `/api/users` | `List<User>` | Uses `RestTemplate.exchange(...)` with `ParameterizedTypeReference<List<User>>`. |
| List active users | `GET` | `/api/users/active` | `List<User>` | Same list handling as the full collection read. |
| Read user by id | `GET` | `/api/users/{id}` | `User` | Uses `getForObject(...)`. |
| Read user by username | `GET` | `/api/users/username/{username}` | `User` | Uses `getForObject(...)`. |
| Create user | `POST` | `/api/users` | `User` | Sends a `User` request body and expects a `User` response. |
| Update user | `PUT` | `/api/users/{id}` | `void` | Sends a `User` request body and ignores the response body. |
| Delete user | `DELETE` | `/api/users/{id}` | `void` | No request body. |
| Deactivate user | `PATCH` | `/api/users/{id}/deactivate` | `void` | Sends `null` as the request body and ignores the response body. |
| Activate user | `PATCH` | `/api/users/{id}/activate` | `void` | Sends `null` as the request body and ignores the response body. |

## Request and response assumptions

`UserApiClient` assumes the producer returns JSON payloads that Spring can deserialize directly into the consumer-side `User` model and `List<User>` collections. The client does not add a custom serializer, deserializer, or response wrapper for these endpoints.

The collection reads depend on `RestTemplate.exchange(...)` and `ParameterizedTypeReference<List<User>>() {}`, which means the consumer expects the producer to return a JSON array of user objects rather than a paged envelope or another wrapper shape.

For the single-item reads and the create call, the client expects a direct `User` response body. For update, delete, activate, and deactivate, the client does not inspect a response body at all.

## Null and empty handling

The consumer does not implement explicit null or empty guarding in `UserApiClient`:

- `getAllUsers()` and `getActiveUsers()` return `response.getBody()` directly, so an empty or missing body is passed through as-is.
- `getUserById()` and `getUserByUsername()` delegate to `RestTemplate.getForObject(...)`, so missing-response handling is delegated to Spring's client behavior.
- `createUser()` returns the direct `postForObject(...)` result without local validation of the returned body.
- `updateUser()`, `deleteUser()`, `deactivateUser()`, and `activateUser()` ignore response content and rely on the HTTP call itself to succeed.

Any stronger null checks, empty collection defaults, or error translation would need to be added above this client layer; they are not present here.

## Runtime request flow

```mermaid
sequenceDiagram
    participant Runner as Demo flow
    participant Client as UserApiClient
    participant API as User API producer

    Runner->>Client: call list, read, create, update, delete, activate, deactivate methods
    Client->>API: HTTP request to baseUrl plus /api/users paths
    API-->>Client: JSON user object, JSON user list, or empty response
    Client-->>Runner: User, List of User, or void
```

The diagram shows the outbound path used by the consumer: a configured base URL plus fixed `/api/users` routes, with Spring handling the HTTP exchange and payload conversion.

## Change boundaries

This page documents the consumer-facing contract only. If the producer adds or renames endpoints, the primary change point in this repository is `UserApiClient`, followed by any service or demo code that calls the affected method.
