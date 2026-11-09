package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
class AuthController {
    record Registration(@NotBlank @Email @Size(max=255) String email,
                        @NotBlank @Size(min=10, max=72) String password,
                        @NotBlank @Size(min=2, max=100) String name,
                        @NotNull Role role) {
        @Override public String toString() { return "Registration[credentials redacted]"; }
    }
    record Login(@NotBlank @Email @Size(max=255) String email,
                 @NotBlank @Size(min=10, max=72) String password) {
        @Override public String toString() { return "Login[credentials redacted]"; }
    }
    private final DemoAuth auth;
    AuthController(DemoAuth auth) { this.auth = auth; }

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    Session register(@Valid @RequestBody Registration input) { return auth.register(input.email(), input.password(), input.name(), input.role()); }

    @PostMapping("/login")
    Session login(@Valid @RequestBody Login input) { return auth.login(input.email(), input.password()); }

    @GetMapping("/me")
    Session me(@RequestHeader(value="Authorization", required=false) String authorization) { return auth.me(authorization); }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    void logout(@RequestHeader(value="Authorization", required=false) String authorization) { auth.logout(authorization); }
}
