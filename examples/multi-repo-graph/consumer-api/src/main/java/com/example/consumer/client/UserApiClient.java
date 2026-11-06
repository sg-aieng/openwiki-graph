package com.example.consumer.client;

import com.example.consumer.model.User;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.List;

@Component
public class UserApiClient {
    private final RestTemplate restTemplate;
    private final String baseUrl;

    public UserApiClient(RestTemplate restTemplate, 
                        @Value("${user.api.base-url}") String baseUrl) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
    }

    public List<User> getAllUsers() {
        ResponseEntity<List<User>> response = restTemplate.exchange(
            baseUrl + "/api/users",
            HttpMethod.GET,
            null,
            new ParameterizedTypeReference<List<User>>() {}
        );
        return response.getBody();
    }

    public List<User> getActiveUsers() {
        ResponseEntity<List<User>> response = restTemplate.exchange(
            baseUrl + "/api/users/active",
            HttpMethod.GET,
            null,
            new ParameterizedTypeReference<List<User>>() {}
        );
        return response.getBody();
    }

    public User getUserById(Long id) {
        return restTemplate.getForObject(
            baseUrl + "/api/users/" + id,
            User.class
        );
    }

    public User getUserByUsername(String username) {
        return restTemplate.getForObject(
            baseUrl + "/api/users/username/" + username,
            User.class
        );
    }

    public User createUser(User user) {
        return restTemplate.postForObject(
            baseUrl + "/api/users",
            user,
            User.class
        );
    }

    public void updateUser(Long id, User user) {
        restTemplate.put(
            baseUrl + "/api/users/" + id,
            user
        );
    }

    public void deleteUser(Long id) {
        restTemplate.delete(baseUrl + "/api/users/" + id);
    }

    public void deactivateUser(Long id) {
        restTemplate.patchForObject(
            baseUrl + "/api/users/" + id + "/deactivate",
            null,
            Void.class
        );
    }

    public void activateUser(Long id) {
        restTemplate.patchForObject(
            baseUrl + "/api/users/" + id + "/activate",
            null,
            Void.class
        );
    }
}
