---
type: concept
title: User Domain Model
description: Consumer-side user DTO shape and the fields used for listing, lookup, creation, filtering, and active-user counts.
tags: [domain-model, dto, users, consumer-integration]
verified:
  - by: openwiki/0.7.3
    at: 2026-11-04T17:34:57.507Z
sources:
  - id: openwiki-source-b6997fdb3ca346a82e33e462
    resource: repo://src/main/java/com/example/consumer/client/UserApiClient.java
  - id: openwiki-source-d27bc4b4253e020a9e94d31e
    resource: repo://src/main/java/com/example/consumer/model/User.java
  - id: openwiki-source-8fa393e301a20a1f82c4d14e
    resource: repo://src/main/java/com/example/consumer/service/UserManagementService.java
generated: { by: "openwiki/0.7.3", at: "2026-11-04T17:34:57.507Z" }
---

# User Domain Model

The consumer treats `User` as a simple transport and display model for the user API. It carries the fields the client prints, sends back on create and update, and reads for local filtering.

## Fields used by the consumer

- `id` (`Long`): returned by lookup and list calls and shown in detail output, but not set by the create helper.
- `username` (`String`): used for display, lookup by username, and user creation and update payloads.
- `email` (`String`): used for display and for the local `getUserEmailsByDomain` filter.
- `fullName` (`String`): used for display and user creation and update payloads.
- `createdAt` (`LocalDateTime`): present on the model for server-populated timestamps, but the consumer does not set or inspect it directly.
- `active` (`boolean`): used in printed output and implied by the active-user endpoints and activate or deactivate operations.

## Consumer assumptions

The client code expects the API to return `User` objects for list and lookup operations, including active-user listings. It also assumes that active status can be toggled through dedicated activate and deactivate endpoints rather than by mutating the `active` field locally.

`createdAt` is modeled as part of the data contract, which suggests the server may populate it, but this repository does not enforce a non-null guarantee or otherwise depend on it in business logic.

## How the model is used

- **Display**: `displayAllUsers`, `displayActiveUsers`, `displayUserById`, `displayUserByUsername`, and `createNewUser` print `User` instances directly.
- **Mutation**: `createNewUser` and `updateExistingUser` build a `User` with `username`, `email`, and `fullName` before sending it to the API.
- **Filtering**: `getUserEmailsByDomain` filters the full user list by `email` suffix.
- **Counts**: `countActiveUsers` derives the count from the size of the active-user list.

```mermaid
erDiagram
    User {
        Long id
        String username
        String email
        String fullName
        LocalDateTime createdAt
        boolean active
    }
```

The diagram shows the fields carried by the consumer-side `User` model.
