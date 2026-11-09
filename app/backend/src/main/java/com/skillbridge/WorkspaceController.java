package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
class WorkspaceController {
    private final DemoAuth auth;
    private final WorkspaceService service;
    WorkspaceController(DemoAuth auth, WorkspaceService service) { this.auth = auth; this.service = service; }
    @GetMapping("/health") Map<String, Object> health() { return service.health(); }
    @PostMapping("/auth/demo") Session login(@Valid @RequestBody DemoLogin input) { return auth.login(input.role()); }
    @GetMapping("/projects") List<ObjectNode> projects() { return service.publicProjects(); }
    @GetMapping("/projects/{id}") ObjectNode project(@PathVariable String id) { return service.publicProject(id); }
    @GetMapping("/projects/participating") List<ObjectNode> participating(@RequestHeader(value="Authorization", required=false) String token) { return service.participatingProjects(auth.require(token, Role.PERSON)); }
    @GetMapping("/company/projects") List<ObjectNode> ownProjects(@RequestHeader(value="Authorization", required=false) String token) { return service.companyProjects(auth.require(token, Role.COMPANY)); }
    @GetMapping("/company/projects/{id}") ObjectNode ownProject(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.companyProject(auth.require(token, Role.COMPANY), id); }
    @GetMapping("/company/projects/{id}/versions") List<ObjectNode> versions(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.versions(auth.require(token, Role.COMPANY), id); }
    @PostMapping("/company/requests") @ResponseStatus(HttpStatus.ACCEPTED) ObjectNode create(@RequestHeader(value="Authorization", required=false) String token, @Valid @RequestBody NewRequest input) { return service.create(auth.require(token, Role.COMPANY), input); }
    @PostMapping("/company/projects/{id}/revise") @ResponseStatus(HttpStatus.ACCEPTED) ObjectNode revise(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id, @Valid @RequestBody Feedback input) { return service.revise(auth.require(token, Role.COMPANY), id, input.feedback()); }
    @PostMapping("/company/projects/{id}/publish") ObjectNode publish(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.publish(auth.require(token, Role.COMPANY), id); }
    @PostMapping("/company/projects/{id}/retry") @ResponseStatus(HttpStatus.ACCEPTED) ObjectNode retry(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.retry(auth.require(token, Role.COMPANY), id); }
    @PostMapping("/company/projects/{id}/clarifications") @ResponseStatus(HttpStatus.ACCEPTED) ObjectNode clarify(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id, @Valid @RequestBody Answers input) { return service.clarify(auth.require(token, Role.COMPANY), id, input); }
    @PostMapping("/company/projects/{id}/close") ObjectNode close(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.close(auth.require(token, Role.COMPANY), id); }
    @GetMapping("/applications") List<ObjectNode> applications(@RequestHeader(value="Authorization", required=false) String token) { return service.applications(auth.require(token, Role.PERSON)); }
    @GetMapping("/applications/{id}") ObjectNode application(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.getApplication(auth.require(token, Role.PERSON), id); }
    @PostMapping("/applications") @ResponseStatus(HttpStatus.CREATED) ObjectNode apply(@RequestHeader(value="Authorization", required=false) String token, @Valid @RequestBody Apply input) { return service.apply(auth.require(token, Role.PERSON), input); }
    @PostMapping("/applications/{id}/work") ObjectNode save(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id, @Valid @RequestBody Work input) { return service.save(auth.require(token, Role.PERSON), id, input, false); }
    @PostMapping("/applications/{id}/submit") ObjectNode submit(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id, @Valid @RequestBody Work input) { return service.save(auth.require(token, Role.PERSON), id, input, true); }
    @PostMapping("/applications/{id}/answers") @ResponseStatus(HttpStatus.ACCEPTED) ObjectNode answers(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id, @Valid @RequestBody Answers input) { return service.answer(auth.require(token, Role.PERSON), id, input); }
    @PostMapping("/applications/{id}/portfolio") ObjectNode portfolio(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.portfolio(auth.require(token, Role.PERSON), id); }
    @GetMapping("/company/submissions") List<ObjectNode> submissions(@RequestHeader(value="Authorization", required=false) String token) { return service.companySubmissions(auth.require(token, Role.COMPANY)); }
    @GetMapping("/company/submissions/{id}") ObjectNode submission(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.companySubmission(auth.require(token, Role.COMPANY), id); }
    @PostMapping("/company/submissions/{id}/finalize") ObjectNode finalizeReport(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id, @Valid @RequestBody Feedback input) { return service.finalizeReport(auth.require(token, Role.COMPANY), id, input.feedback()); }
    @GetMapping("/jobs/{id}") ObjectNode job(@RequestHeader(value="Authorization", required=false) String token, @PathVariable String id) { return service.job(auth.require(token, null), id); }
}
