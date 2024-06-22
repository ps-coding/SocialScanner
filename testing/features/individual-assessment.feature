Feature: Individual Assessment
  The individual assessment should provide the appropriate result in a new window based on the Instagram account and grades provided.

  Background:
    Given the app has just been launched

  Scenario: No input data provided
    Given the user has not filled any fields
    When the user clicks the "Run Individual Assessment" button
    Then the user should see an error message that says "Please enter an Instagram account and/or grades."

  Scenario: Only Instagram account "serialkillerspodcast" provided
    Given the user has filled the Instagram account field with "serialkillerspodcast"
    And the user has not filled the grades field
    When the user clicks the "Run Individual Assessment" button
    Then the user should see a new window that displays a result of approximately -0.9 in red, lists the 20 analyzed posts, and notes that "No grades could be compared."

  Scenario: Only grades "math:50" and "science:50" provided
    Given the user has not filled the Instagram account field
    And the user has filled the previous grades as "math:50" and "science:50"
    And the user has filled the current grades as "math:60" and "science:60"
    When the user clicks the "Run Individual Assessment" button
    Then the user should see a new window that displays 0.1 in yellow, lists "math: 0.1" and "science: 0.1," and notes, "No Instagram account provided."

  Scenario: Instagram account "6amsuccess" and grades "math:50" and "science:50" provided
    Given the user has filled the Instagram account field with "6amsuccess"
    And the user has filled the previous grades as "math:50" and "science:50"
    And the user has filled the current grades as "math:60" and "science:60"
    When the user clicks the "Run Individual Assessment" button
    Then the user should see a new window that displays approximately 0.3 in yellow as the main result, displays an Instagram score of approximately 0.5 in green, lists the 20 analyzed posts, displays a grade score of 0.1 in yellow, and lists "math: 0.1" and "science: 0.1"
