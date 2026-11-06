package com.example.consumer.runner;

import com.example.consumer.model.User;
import com.example.consumer.service.UserManagementService;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class DemoRunner implements CommandLineRunner {
    private final UserManagementService userManagementService;

    public DemoRunner(UserManagementService userManagementService) {
        this.userManagementService = userManagementService;
    }

    @Override
    public void run(String... args) throws Exception {
        System.out.println("\n========================================");
        System.out.println("User API Consumer Demo");
        System.out.println("========================================");

        userManagementService.displayAllUsers();

        userManagementService.displayActiveUsers();

        userManagementService.displayUserById(1L);

        userManagementService.displayUserByUsername("john_doe");

        User newUser = userManagementService.createNewUser(
            "alice_wonder", 
            "alice@example.com", 
            "Alice Wonderland"
        );

        if (newUser != null && newUser.getId() != null) {
            userManagementService.updateExistingUser(
                newUser.getId(),
                "alice_wonder",
                "alice.wonderland@example.com",
                "Alice in Wonderland"
            );

            userManagementService.deactivateUserAccount(newUser.getId());

            userManagementService.activateUserAccount(newUser.getId());
        }

        System.out.println("\n=== Users with example.com domain ===");
        System.out.println(userManagementService.getUserEmailsByDomain("example.com"));

        System.out.println("\n=== Active User Count ===");
        System.out.println("Total active users: " + userManagementService.countActiveUsers());

        System.out.println("\n========================================");
        System.out.println("Demo Complete!");
        System.out.println("========================================\n");
    }
}
