---
type: quickstart
title: Quickstart
description: Entry point for the producer-api wiki — routes to the right page for running the service, exploring endpoints, understanding the data model, or modifying service logic.
tags: [quickstart, navigation, getting-started]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-02T03:32:07.279Z
sources:
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-c7f84d3f13f5f73cca00d717
    resource: repo://src/main/java/com/example/userapi/service/UserService.java
  - id: openwiki-source-ece093ad10b91f3da0b7e34f
    resource: repo://src/main/resources/application.properties
generated: { by: "claude-code", at: "2026-11-02T03:32:07.279Z" }
---

# Quickstart

`producer-api` is a Spring Boot 3.2 REST API for user management. All state is held in memory; no database is required.

## Run the service

```bash
./mvnw spring-boot:run
```

The API is available at `http://localhost:8080`. Three seed users (admin, john_doe, jane_smith) are created automatically on every startup.

To build a runnable JAR:

```bash
./mvnw clean package
java -jar target/user-api-producer-1.0.0.jar
```

## Task routing

| I want to… | Go to |
|------------|-------|
| See all available endpoints and their request/response shapes | [User API Endpoints](api/endpoints.md) |
| Understand how the application is structured | [Architecture Overview](architecture/overview.md) |
| Know the User fields, validation rules, and lifecycle | [User Model](data/user-model.md) |
| Modify an existing endpoint | [UserController](../src/main/java/com/example/userapi/controller/UserController.java) → [User API Endpoints](api/endpoints.md) |
| Change business logic or storage | [UserService](../src/main/java/com/example/userapi/service/UserService.java) → [Architecture Overview](architecture/overview.md) |
| Add a field or change validation | [User](../src/main/java/com/example/userapi/model/User.java) → [User Model](data/user-model.md) |

## Key facts

- **No persistence** — all data is lost on restart; seed users are recreated each time.
- **Port** — `8080` (set via `server.port` in `application.properties`).
- **Base path** — `/api/users`.
- **Validation** — `username` and `email` are required; email must be well-formed. No uniqueness enforcement.
- **Active flag** — users can be soft-deactivated with `PATCH /{id}/deactivate` and reactivated with `PATCH /{id}/activate`.
