# Stage 4 Report – MVP Development and Execution

## Project Title
**Human-in-the-Loop AI Guardian for Connected Aerospace Systems**

## 1. Introduction

This stage focuses on implementing the MVP based on the technical documentation developed in the previous stage. It is the most execution-intensive phase of the project, where plans and designs are translated into a working prototype.

The purpose of this stage is to:
- implement the MVP features
- divide work into manageable sprints
- assign clear roles and responsibilities
- maintain source control and quality assurance discipline
- monitor progress and adjust when necessary
- prepare the project for final integration, review, and presentation

By following an Agile-inspired workflow, the team can work iteratively, improve continuously, and remain aligned throughout development.

---

## 2. Stage 4 Objectives

The objectives of this stage are:
- implement the MVP based on the technical documentation from Stage 3
- adopt Agile principles to divide work into manageable sprints
- assign clear roles and responsibilities, especially for Project Manager, SCM, and QA
- promote collaboration through clear task ownership, deadlines, and dependencies
- monitor progress using metrics and adjust the plan when necessary
- prepare the project for final technical manual review

---

## 3. Importance of Stage 4

This stage represents the most intensive phase of the project. It transforms the technical plan into a functional MVP through focused development, testing, integration, and review.

Non-technical roles such as:
- **Project Manager**
- **Source Control Manager**
- **Quality Assurance**

are essential to maintaining organization, ensuring code quality, and delivering a stable result.

The adoption of Agile principles helps the team remain:
- organized
- adaptable
- collaborative
- delivery-focused

---

## 4. Key Roles for Stage 4

| Role | Purpose |
|---|---|
| **Project Manager (PM)** | Oversees sprint planning, tracks progress, coordinates the team, and adapts the plan when needed. |
| **Source Control Manager (SCM)** | Ensures proper use of Git and GitHub, protects branch quality, and supports code review discipline. |
| **Quality Assurance (QA)** | Verifies that completed features work as expected and helps validate quality before presentation. |
| **Technical Roles** | Implement the MVP components such as telemetry processing, database, dashboard, APIs, and integration logic. |

### 4.1 Stage 4 Role Assignment

| Role | Assigned To | Responsibilities |
|---|---|---|
| **Project Manager (PM)** | **Kedia Ihogoza** | Oversees sprint planning, tracks progress, coordinates priorities, and manages blockers or changes in scope. |
| **Source Control Manager (SCM)** | **Shared, led by Kedia** | Ensures clean branch usage, consistent commit messages, review of important changes, and good Git/GitHub practices. |
| **Quality Assurance (QA)** | **Shared** | Verifies outputs, validates anomaly scenarios, reviews results, and confirms readiness for integration and presentation. |
| **Core Development** | **Kedia Ihogoza** | Develops the telemetry pipeline, Guardian logic, replay system, anomaly detection, ML scoring, and technical integration with the aircraft side. |
| **Database and Dashboard Development** | **Davi Roset** | Develops the database structure, telemetry/alert storage logic, and dashboard views for operator monitoring and review. |

---

## 5. Stage 4 Tasks

The main tasks for this stage are:
- plan and define sprints
- execute development tasks
- monitor progress and adjust
- conduct sprint reviews and retrospectives
- perform final integration and QA testing
- prepare for the technical manual review

---

## 6. Sprint Strategy

### 6.1 Sprint Approach

The development phase is divided into short, manageable sprints. Each sprint includes:
- sprint planning
- task execution
- progress follow-up
- code review
- QA testing
- sprint review
- sprint retrospective

Because the team is small, the process remains lightweight, but it still follows Agile principles.

### 6.2 Suggested Activities for Each Sprint

| Activity | Purpose |
|---|---|
| **Sprint Planning** | Define sprint goals, assign tasks, and set deadlines. |
| **Daily Stand-Ups** | Discuss progress, blockers, and next steps. |
| **Development** | Implement features according to the sprint plan. |
| **Code Reviews** | Review important changes before merging. |
| **QA Testing** | Validate completed tasks and detect issues early. |
| **Sprint Review** | Present completed work and confirm progress. |
| **Sprint Retrospective** | Reflect on what worked well and what should improve. |

---

## 7. Sprint Plan

### 7.1 Sprint 1 – Core Guardian and Replay Validation

**Sprint Goal:**  
Stabilize the Guardian core and validate anomaly detection on replayed telemetry scenarios.

| Task | Priority | Assigned To | Deadline / Sprint | Expected Output |
|---|---|---|---|---|
| Finalize replay pipeline | Must Have | Kedia | Sprint 1 | Replay module reads scenarios reliably |
| Validate rule-based anomaly detection | Must Have | Kedia | Sprint 1 | Core anomalies detected correctly |
| Refine telemetry schema consistency | Must Have | Kedia & Davi | Sprint 1 | Stable field definitions shared across modules |
| Integrate supporting ML anomaly score | Should Have | Kedia | Sprint 1 | Isolation Forest added as supporting score |
| Draft initial database structure | Must Have | Davi | Sprint 1 | Schema prepared for telemetry, alerts, and actions |

### 7.2 Sprint 2 – Database and Dashboard Integration

**Sprint Goal:**  
Connect Guardian outputs to storage and visualization layers.

| Task | Priority | Assigned To | Deadline / Sprint | Expected Output |
|---|---|---|---|---|
| Implement telemetry storage | Must Have | Davi | Sprint 2 | Telemetry records stored in the database |
| Implement alert storage | Must Have | Davi | Sprint 2 | Structured alerts saved correctly |
| Build initial dashboard views | Must Have | Davi | Sprint 2 | Dashboard shows telemetry and alerts |
| Align backend and Guardian outputs | Must Have | Kedia & Davi | Sprint 2 | Stable contract between detection logic and dashboard |
| Add operator action logging | Should Have | Davi | Sprint 2 | Acknowledge / override / escalate actions stored |

### 7.3 Sprint 3 – Final Testing and Presentation Readiness

**Sprint Goal:**  
Prepare the MVP for final testing, review, and school presentation.

| Task | Priority | Assigned To | Deadline / Sprint | Expected Output |
|---|---|---|---|---|
| Run final anomaly scenario tests | Must Have | Shared | Sprint 3 | Verified outputs on all core scenarios |
| Improve documentation and README | Must Have | Kedia | Sprint 3 | Clear and updated repository documentation |
| Refine dashboard usability | Should Have | Davi | Sprint 3 | Cleaner interface for demo use |
| Prepare manual review explanations | Must Have | Shared | Sprint 3 | Team ready to explain code, architecture, and testing |
| Final integration and demo preparation | Must Have | Shared | Sprint 3 | MVP ready for school presentation |

---

## 8. Dependencies

Some tasks depend on the completion of earlier technical elements.

| Task | Depends On |
|---|---|
| Dashboard alert display | Stable alert structure from the Guardian |
| Database integration | Defined telemetry and alert schemas |
| Operator action logging | Dashboard alert workflow |
| Final testing | Core Guardian logic and dashboard integration |
| Final presentation | Validated MVP and updated documentation |

---

## 9. Execute Development Tasks

During development:
- technical work is divided according to sprint priorities
- each team member focuses on assigned deliverables
- development follows the documented system design
- tasks are updated regularly based on progress and blockers

### 9.1 Development Responsibilities

| Area | Assigned To |
|---|---|
| Guardian logic and replay system | Kedia |
| Anomaly detection and ML score | Kedia |
| Database design and storage | Davi |
| Dashboard and visualization | Davi |
| Shared testing and review | Shared |

---

## 10. Monitor Progress and Adjust

Progress is monitored throughout the stage to ensure that the team remains aligned with the MVP goals.

### 10.1 Monitoring Methods

- regular stand-ups or check-ins
- GitHub progress and commit history
- task updates in a tracking tool such as Trello
- review of sprint completion against planned tasks

### 10.2 Example Metrics

| Metric | Purpose |
|---|---|
| Sprint velocity | Measure how many planned tasks are completed per sprint |
| Completion rate | Compare completed tasks vs. planned tasks |
| Bug count | Track the number of issues identified during testing |
| Bug resolution rate | Measure how quickly detected issues are fixed |

### 10.3 Adjustments

If progress deviates from the plan:
- priorities will be reviewed
- non-essential tasks may be postponed
- shared tasks may be redistributed
- replay-based testing remains the fallback if live telemetry is delayed

---

## 11. Sprint Reviews and Retrospectives

At the end of each sprint, the team will:
- review completed work
- confirm whether the sprint goal was reached
- identify blockers or missed tasks
- discuss improvements for the next sprint

### 11.1 Review Questions

- What was completed during the sprint?
- What remains incomplete?
- What should be demonstrated to stakeholders?

### 11.2 Retrospective Questions

- What worked well during the sprint?
- What challenges did we face?
- What can be improved in the next sprint?

---

## 12. Final Integration and QA Testing

### 12.1 Purpose

The purpose of the final integration and QA phase is to ensure that all system components work together correctly and that the MVP meets expected quality standards.

### 12.2 QA Methods

- scenario testing using replayed CSV files
- functional verification of alerts
- manual review of outputs and recommended actions
- integration testing between Guardian, database, dashboard, and operator workflow

### 12.3 Test Scenarios

| Scenario | Expected Result |
|---|---|
| Normal flight | No false alerts generated |
| Packet loss | Packet loss alert generated |
| Sensor dropout | IMU dropout alert generated |
| Low battery | Low battery alert generated |
| GPS jump | GPS anomaly detected |
| GPS/IMU inconsistency | Inconsistency alert generated |

### 12.4 QA Goal

The QA goal is to confirm that the Guardian:
- behaves correctly on normal data
- detects defined anomalies
- produces understandable outputs
- remains traceable and testable
- is stable enough for final review and demonstration

---

## 13. Deliverables

The final deliverables for this stage should include links to all relevant project artifacts.

| Deliverable | Description |
|---|---|
| Sprint planning | Sprint plan with tasks, deadlines, and responsibilities |
| Sprint reviews | Summary or evidence of sprint outcomes |
| Retrospectives | Notes on what worked and what should improve |
| Source repository | GitHub repository link |
| Bug tracking | Evidence of issue tracking or bug resolution |
| Testing evidence and results | Validation results, scenario testing, screenshots, or notes |
| Production / demo environment | Working MVP environment for demonstration, if available |

---

## 14. Technical Manual Review

At the end of this stage, the project will be evaluated through a technical manual review.

### 14.1 What the Review Will Validate

The review will evaluate:
- completion of the project as a functional MVP
- demonstration of the MVP
- quality of the code, commits, and documentation
- ability to explain technical decisions logically
- ability to explain application features and code in detail
- understanding of how the application works
- explanation of testing methods and results
- explanation of team collaboration
- use of Git and GitHub best practices
- understanding of frontend, backend, database, and other technical concepts applied in the MVP

### 14.2 What Must Be Prepared

Before the review, the team should prepare:
- a functional application
- application diagrams
- the database diagram
- a clean and professional README
- a GitHub repository ready to present
- a repository that includes:
  - application architecture
  - database diagram
  - complete codebase
  - clear documentation

### 14.3 Why It Matters

This review is a crucial validation step. It confirms not only that the MVP works, but also that the team can explain the technical reasoning, implementation choices, testing approach, and collaboration process behind the project.

---

## 15. Tips for Success

- Focus on communication to resolve blockers quickly
- Use tools such as Trello or GitHub Projects to track work
- Stay flexible and adapt sprint scope when needed
- Integrate QA into every sprint
- Keep the MVP focused on the most important deliverables
- Maintain documentation and diagrams alongside development

---

## 16. Conclusion

Stage 4 transforms planning and technical design into an executable MVP. Through sprint-based organization, clear role distribution, and integrated testing, the team can focus on delivering a functional and presentable prototype.

This stage also prepares the team for final validation by ensuring that both the implementation and the explanations behind it are ready for review.
