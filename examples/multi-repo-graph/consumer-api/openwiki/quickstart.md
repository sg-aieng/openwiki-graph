---
type: quickstart guide
title: Quickstart
description: Start the Spring Boot consumer application, point it at the User API producer, and jump to the deeper wiki pages for architecture, concepts, workflow, and operations.
tags: [quickstart, spring-boot, consumer, user-api]
verified:
  - by: openwiki/0.7.3
    at: 2026-11-04T17:34:57.507Z
sources:
  - id: openwiki-source-2355f81d7cf522f8dbdaabd4
    resource: repo://pom.xml
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-44f28c3920f1fd9c787c3efd
    resource: repo://src/main/java/com/example/consumer/ConsumerApplication.java
  - id: openwiki-source-ece093ad10b91f3da0b7e34f
    resource: repo://src/main/resources/application.properties
generated: { by: "openwiki/0.7.3", at: "2026-11-04T17:34:57.507Z" }
---

# Quickstart

This page is the entry point for the consumer app wiki. Use it to start the app, confirm the required upstream service, and navigate to the more detailed pages.

## What you need before starting

The consumer is a Spring Boot 3.2 application built with Java 17 and Maven. Its runtime depends on the User API producer being available at the configured base URL, which defaults to `http://localhost:8080`.

## Start the application

From the repository root:

```bash
./mvnw clean install
./mvnw spring-boot:run
```

The application starts from `com.example.consumer.ConsumerApplication`, and it registers a `RestTemplate` bean for outbound HTTP calls to the producer.

## Runtime expectations

Set the producer location in `src/main/resources/application.properties` if you do not want the default local endpoint:

```properties
user.api.base-url=http://localhost:8080
```

When the consumer starts, it is designed to run its demo flow automatically and print results to the console. If the producer is not reachable, the demo cannot complete successfully.

## Where to read next

- [Application Overview](architecture/application-overview.md) — the consumer app structure and major components
- [User Domain Model](concepts/user-domain.md) — the user shape and domain assumptions used by the consumer
- [Configuration and Runtime](operations/configuration-and-runtime.md) — configuration, startup, and troubleshooting notes
- [Demo Execution Workflow](workflows/demo-execution.md) — the startup-to-demo sequence and the actions the runner performs

## Repository references

Useful source files for orientation:

- `README.md`
- `pom.xml`
- `src/main/java/com/example/consumer/ConsumerApplication.java`
- `src/main/resources/application.properties`
