package com.example.consumer.service;

import com.example.consumer.client.UserApiClient;
import com.example.consumer.model.User;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class UserManagementService {
    private final UserApiClient userApiClient;

    public UserManagementService(UserApiClient userApiClient) {
        this.userApiClient = userApiClient;
    }

    public void displayAllUsers() {
        System.out.println("\n=== All Users ===");
        List<User> users = userApiClient.getAllUsers();
        users.forEach(System.out::println);
    }

    public void displayActiveUsers() {
        System.out.println("\n=== Active Users ===");
        List<User> activeUsers = userApiClient.getActiveUsers();
        activeUsers.forEach(System.out::println);
    }

    public void displayUserById(Long id) {
        System.out.println("\n=== User Details (ID: " + id + ") ===");
        User user = userApiClient.getUserById(id);
        System.out.println(user);
    }

    public void displayUserByUsername(String username) {
        System.out.println("\n=== User Details (Username: " + username + ") ===");
        User user = userApiClient.getUserByUsername(username);
        System.out.println(user);
    }

    public User createNewUser(String username, String email, String fullName) {
        System.out.println("\n=== Creating New User ===");
        User newUser = new User(username, email, fullName);
        User created = userApiClient.createUser(newUser);
        System.out.println("Created: " + created);
        return created;
    }

    public void updateExistingUser(Long id, String username, String email, String fullName) {
        System.out.println("\n=== Updating User ===");
        User updatedUser = new User(username, email, fullName);
        userApiClient.updateUser(id, updatedUser);
        System.out.println("Updated user ID: " + id);
    }

    public void removeUser(Long id) {
        System.out.println("\n=== Deleting User ===");
        userApiClient.deleteUser(id);
        System.out.println("Deleted user ID: " + id);
    }

    public void deactivateUserAccount(Long id) {
        System.out.println("\n=== Deactivating User ===");
        userApiClient.deactivateUser(id);
        System.out.println("Deactivated user ID: " + id);
    }

    public void activateUserAccount(Long id) {
        System.out.println("\n=== Activating User ===");
        userApiClient.activateUser(id);
        System.out.println("Activated user ID: " + id);
    }

    public List<String> getUserEmailsByDomain(String domain) {
        List<User> users = userApiClient.getAllUsers();
        return users.stream()
                .map(User::getEmail)
                .filter(email -> email.endsWith("@" + domain))
                .collect(Collectors.toList());
    }

    public long countActiveUsers() {
        return userApiClient.getActiveUsers().size();
    }
}
