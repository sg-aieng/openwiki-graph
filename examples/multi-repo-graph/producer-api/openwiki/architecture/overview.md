---
type: architecture
title: Architecture Overview
description: Three-layer Spring Boot architecture for the User API — Controller, Service, and in-memory store — including wiring, startup seeding, and thread-safety model.
tags: [architecture, spring-boot, layers, concurrency, in-memory]
verified:
  - by: openwiki/0.7.2
    at: 2026-11-02T03:32:07.279Z
sources:
  - id: openwiki-source-2355f81d7cf522f8dbdaabd4
    resource: repo://pom.xml
  - id: openwiki-source-513bde25c0e66ae5c122cef9
    resource: repo://src/main/java/com/example/userapi/controller/UserController.java
  - id: openwiki-source-c7f84d3f13f5f73cca00d717
    resource: repo://src/main/java/com/example/userapi/service/UserService.java
generated: { by: "claude-code", at: "2026-11-02T03:32:07.279Z" }
---

# Architecture Overview

`producer-api` is a Spring Boot 3.2 application packaged as a single executable JAR. It follows a standard three-layer architecture with no external persistence: all state is held in memory for the lifetime of the process.

## Layers

```
HTTP client
    │
    ▼
UserController          (@RestController, /api/users)
    │  constructor-injects
    ▼
UserService             (@Service)
    │  reads/writes
    ▼
ConcurrentHashMap<Long, User>   (in-process, no DB)
```

### Controller

`UserController` (`src/main/java/com/example/userapi/controller/UserController.java`) is the sole entry point for HTTP traffic. It:

- Maps all routes under `/api/users` via `@RequestMapping`.
- Delegates every operation to `UserService` with no business logic of its own.
- Applies `@Valid` on `@RequestBody` parameters to trigger Bean Validation before the call reaches the service.
- Returns `ResponseEntity` wrappers, translating service return values (`null`, `Optional.empty()`, `boolean`) to appropriate HTTP status codes.

### Service

`UserService` (`src/main/java/com/example/userapi/service/UserService.java`) owns all user management logic:

- Holds a `ConcurrentHashMap<Long, User>` as the sole data store.
- Uses an `AtomicLong idGenerator` (starting at 1) for monotonically increasing ID assignment.
- Seeding: the no-arg constructor calls `createUser` three times, producing users `admin` (id=1), `john_doe` (id=2), and `jane_smith` (id=3) on every cold start. These seed records are not persisted and are lost on restart.

### Entry point

`UserApiApplication` (`src/main/java/com/example/userapi/UserApiApplication.java`) is annotated with `@SpringBootApplication` and delegates to `SpringApplication.run`. Component scanning covers the `com.example.userapi` package and its sub-packages automatically.

## Concurrency model

`ConcurrentHashMap` provides segment-level thread safety for independent key operations (get, put, remove). The `AtomicLong` guarantees unique ID assignment under concurrent creates. However, read-modify-write sequences (e.g. `deactivateUser`: get then set field) are not atomically protected — concurrent updates to the same user record can interleave. This is acceptable for a demo/prototype workload.

## Configuration

`src/main/resources/application.properties` sets:

| Key | Value | Effect |
|-----|-------|--------|
| `server.port` | `8080` | HTTP listen port |
| `spring.application.name` | `user-api-producer` | Used in Spring context and actuator |
| `logging.level.com.example.userapi` | `INFO` | Package-level log verbosity |

## Build and runtime

The project uses Spring Boot Maven plugin (`spring-boot-maven-plugin`) with Java 17. Build and run:

```bash
./mvnw clean install
./mvnw spring-boot:run
```

The fat JAR produced by `mvn package` is self-contained and needs no external server.

## Dependencies

Core dependencies declared in `pom.xml`:

- `spring-boot-starter-web` — embedded Tomcat + Spring MVC
- `spring-boot-starter-validation` — Hibernate Validator / Bean Validation
- `spring-boot-starter-test` — JUnit 5, Mockito, Spring Test (test scope)
