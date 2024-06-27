Feature: Mass Assessment
  The mass assessment should provide the appropriate results in new windows based on the Instagram accounts provided.

  Background:
    Given the app has been launched
    And the user has clicked the "Configure Mass Assessment" button

  Scenario: Nothing is entered
    Given the user has not entered any Instagram accounts
    When the "Run Mass Assessment" button is clicked
    Then the user should see an error message that says "Please add at least one Instagram account."

  Scenario: "serialkillerspodcast" and "6amsuccess" have been entered without any grades
    Given the user has entered "serialkillerspodcast" and "6amsuccess" into the Instagram accounts field
    When the "Run Mass Assessment" button is clicked
    Then the user should see a window containing the results for "serialkillerspodcast" and "6amsuccess" with a positive green score of approximately 0.5 associated with "6amsuccess" and a negative red score of approximately -0.9 with "serialkillerspodcast". Each label, if selected, can be expanded via a button which opens a new window giving more depth to their mental health – with things like their score, captions, and image details.
