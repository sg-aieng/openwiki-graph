# User API Consumer

A Spring Boot application that consumes the User API to demonstrate various API usage patterns.

## Prerequisites

The User API Producer must be running on `http://localhost:8080`

## Build and Run

```bash
./mvnw clean install
./mvnw spring-boot:run
```

## What It Does

This consumer application demonstrates various ways to use the User API:

1. **Get All Users** - Retrieves and displays all users from the API
2. **Get Active Users** - Filters and displays only active users
3. **Get User by ID** - Fetches a specific user by their ID
4. **Get User by Username** - Looks up a user by username
5. **Create User** - Creates a new user account
6. **Update User** - Updates an existing user's information
7. **Deactivate User** - Marks a user as inactive
8. **Activate User** - Reactivates a deactivated user
9. **Filter by Email Domain** - Demonstrates filtering users by email domain
10. **Count Active Users** - Shows how to aggregate user data

## Key Components

### UserApiClient
The main client class that makes HTTP calls to the User API. It uses Spring's `RestTemplate` to interact with all the API endpoints.

### UserManagementService
A higher-level service that uses `UserApiClient` to perform business operations. This shows how consumers typically wrap API calls in their own service layer.

### DemoRunner
A command-line runner that executes a series of API calls when the application starts, demonstrating all the different usage patterns.

## Configuration

Configure the API base URL in `application.properties`:

```properties
user.api.base-url=http://localhost:8080
```

## Running Both Applications

1. Start the producer:
   ```bash
   cd /Users/sharadgulati/rnd/producer
   ./mvnw spring-boot:run
   ```

2. In a new terminal, start the consumer:
   ```bash
   cd /Users/sharadgulati/rnd/consumer
   ./mvnw spring-boot:run
   ```

The consumer will automatically run the demo when it starts and display the results in the console.
