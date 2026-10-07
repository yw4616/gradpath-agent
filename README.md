# GradPath

GradPath is a domain-specific academic planning assistant for Columbia graduate students. It helps students calculate GPA targets, check graduate program requirements, audit degree progress, and look up Columbia course information through a tool-calling AI agent.

## Tools

- `calculate_gpa_path` — Calculates the GPA needed across a student's remaining credits to reach a target cumulative GPA.
- `lookup_program_requirements` — Looks up requirements for supported Columbia graduate programs using official Columbia sources.
- `audit_degree_requirements` — Compares a student's completed credits and courses against program requirements to identify what is still missing.
- `lookup_course_catalog` — Looks up Columbia course details such as course title, credits, term, instructor, and available sections from the Columbia Bulletin.

## How to Use

Enter a question in the GradPath chat box. The agent will determine whether it needs to call one or more tools and will return an answer based on the tool results.

The interface also displays tool activity, including the tool name, arguments, and result, so users can see how the agent arrived at its answer.

GradPath keeps conversation context within the same session, allowing users to ask follow-up questions without repeating all previously provided information.

## Example Queries

1. `I have a 2.9 GPA after 24 credits and 9 credits left. What GPA do I need to finish with a 3.0?`

2. `What are the requirements for Columbia MS Data Science?`

3. `I'm in Columbia MS Data Science. I have completed 24 credits including COMS W4121 and COMS W4721. What am I still missing?`
