Feature: GoRest user API
  The user resource should support reliable creation, retrieval, and error handling.

  @requires_auth
  Scenario: Happy Path - create a user and validate contract and SLA
    When I create a new GoRest user
    Then the response status should be 201
    And the user response should match the user schema
    And the response time should be less than 2.0 seconds

  @requires_auth
  Scenario: Read Path - fetch a newly created user
    Given I create a new GoRest user
    And the response status should be 201
    When I fetch the created GoRest user
    Then the response status should be 200
    And the user response should match the user schema

  @requires_auth
  Scenario: Update Path - modify an existing user via PATCH
    Given I create a new GoRest user
    And the response status should be 201
    When I update the created GoRest user details
    Then the response status should be 200
    And the user response should match the user schema
    And the user response should reflect the updated details

  Scenario: Negative Path - reject a user creation without a token
    When I create a GoRest user without an authentication token
    Then the response status should be 401

  Scenario: Negative Path - return not found for an absent user
    When I fetch non-existent GoRest user ID 999999999
    Then the response status should be 404
