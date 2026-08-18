# Chapter 1 --- Executive Summary & System Vision

------------------------------------------------------------------------

# Travel Recovery Operating System (TR-OS)

**Version:** 0.1 (Draft)

**Project Type**

Agentic Artificial Intelligence Platform

**Category**

Intelligent Flight Rebooking

**Target Platform**

Atlas Travel Hackathon

**Technology Focus**

-   Agentic AI
-   Multi-Agent Orchestration
-   ReAct Reasoning
-   Event-Driven Systems
-   Explainable AI
-   Autonomous Decision Support

------------------------------------------------------------------------

# 1. Executive Summary

## 1.1 Overview

Travel disruptions are no longer rare events. Flight cancellations,
delays, weather disruptions, overbooked flights, airport congestion, and
operational failures affect millions of passengers every year. While
airlines and travel applications notify passengers about disruptions,
the responsibility of recovering an entire trip still falls almost
entirely on the traveler.

A canceled flight rarely affects only the flight itself.

It creates a cascade of downstream problems including:

-   missed hotel check-ins
-   airport transportation conflicts
-   itinerary changes
-   business meeting delays
-   increased travel costs
-   visa complications
-   insurance claims
-   emotional stress

Current travel platforms solve these problems independently.

One application searches for flights.

Another manages hotels.

Another checks transportation.

Another explains airline policies.

The traveler becomes the system integrator.

**TR-OS removes that burden.**

Instead of helping travelers search for information, the system
autonomously analyzes the disruption, coordinates specialized AI agents,
and generates an optimized recovery strategy that considers the
traveler's entire journey rather than a single booking.

------------------------------------------------------------------------

## 1.2 Vision Statement

> **Transform travel disruption management from fragmented manual
> decision-making into an autonomous, explainable, AI-driven recovery
> experience.**

Instead of asking:

> "Which flight should I book?"

The traveler simply asks:

> "Recover my trip."

The system determines everything else.

------------------------------------------------------------------------

## 1.3 Mission Statement

The mission of TR-OS is not to replace travel agencies.

It is to become an **AI Operating System** capable of coordinating
multiple autonomous agents that collaboratively recover disrupted
journeys while minimizing traveler effort, financial loss, and
uncertainty.

------------------------------------------------------------------------

## 1.4 Product Philosophy

Traditional travel applications are built around **search**.

``` text
Search Flight
↓
Display Results
↓
User Decides
```

TR-OS is built around **missions**.

``` text
Mission
↓
Understand Context
↓
Reason
↓
Coordinate Agents
↓
Validate
↓
Recover Trip
```

The difference is fundamental.

The user no longer performs the reasoning.

The AI performs the reasoning.

------------------------------------------------------------------------

# 2. Problem Definition

## 2.1 Existing Workflow

Today, when a flight is cancelled, a traveler typically follows this
process:

``` text
Flight Cancelled
↓
Search Google
↓
Open Airline App
↓
Search Alternative Flights
↓
Compare Prices
↓
Call Hotel
↓
Contact Airport Transfer
↓
Read Airline Policy
↓
Estimate New Budget
↓
Book Everything
↓
Hope Nothing Else Breaks
```

This workflow is:

-   time consuming
-   stressful
-   repetitive
-   fragmented
-   error-prone

Every change creates another decision.

## 2.2 Root Problem

The real problem is **not flight cancellation**.

The real problem is **decision overload**.

Travelers are forced to make dozens of interconnected decisions while
experiencing uncertainty and time pressure.

Modern AI should not simply answer questions.

It should reduce cognitive load.

------------------------------------------------------------------------

# 3. Proposed Solution

TR-OS introduces a new interaction paradigm.

Instead of interacting with isolated booking services, users initiate a
mission:

> **Recover my trip.**

The mission activates specialized AI agents that collaborate, validate
one another's outputs, and generate a unified recovery strategy.

------------------------------------------------------------------------

# 4. Design Philosophy

## Principle 1 --- Mission-Oriented AI

Every mission has:

-   Objective
-   Context
-   Dependencies
-   Completion Criteria

------------------------------------------------------------------------

## Principle 2 --- Event-Driven Intelligence

Travel events trigger autonomous workflows.

Examples:

-   Flight Cancelled
-   Flight Delayed
-   Gate Changed

------------------------------------------------------------------------

## Principle 3 --- Multi-Agent Collaboration

Specialized agents own specific responsibilities:

-   Flight Recovery
-   Transportation
-   Budget
-   Airline Policy
-   Hotel Management

------------------------------------------------------------------------

## Principle 4 --- Explainable AI

Every recommendation must explain **why** it was chosen.

Example:

-   Earliest arrival
-   Lowest additional cost
-   No visa required
-   Compatible hotel check-in
-   Airport transfer available

------------------------------------------------------------------------

## Principle 5 --- Reflection Before Recommendation

Every recovery plan undergoes an internal validation stage before being
shown to the user.

Question:

> Can this plan be improved?

------------------------------------------------------------------------

# 5. System Scope

Supported:

-   Flight cancellation
-   Flight delay
-   Missed connection
-   Schedule changes

Out of Scope:

-   Autonomous payment
-   Automatic booking
-   Visa submission
-   Insurance claim automation

------------------------------------------------------------------------

# 6. Objectives

1.  Reduce traveler decision-making effort.
2.  Recover an entire journey.
3.  Demonstrate autonomous multi-agent collaboration.
4.  Provide transparent ReAct reasoning.
5.  Produce explainable recommendations.
6.  Showcase scalable orchestration.

------------------------------------------------------------------------

# 7. Success Criteria

-   Detect disruption.
-   Understand traveler context.
-   Coordinate multiple agents.
-   Generate complete recovery strategy.
-   Explain recommendations.
-   Respond within acceptable time.
-   Operate with minimal user intervention.

------------------------------------------------------------------------

# 8. Why This Project Matters

TR-OS explores the transition from conversational AI toward autonomous
AI systems capable of coordinating specialized intelligence. Instead of
building another chatbot, the project demonstrates how event-driven
multi-agent systems, ReAct reasoning, and explainable AI can
collaboratively reduce complexity during travel disruptions.

------------------------------------------------------------------------

## Architect's Note

The next chapter will focus on business analysis rather than
implementation. We will define users, journeys, pain points, functional
requirements, and non-functional requirements before designing the
technical architecture.

---

# Chapter 2 --- Business Analysis & Domain Modeling

## 2.1 Purpose

Before designing agents, APIs, or infrastructure, it is essential to
understand the business domain. TR-OS is designed to reduce traveler
decision fatigue during travel disruptions by transforming fragmented
recovery tasks into a single autonomous mission.

## 2.2 Stakeholders

### Primary

-   Travelers
-   Airlines
-   Online Travel Agencies (OTAs)
-   Airport Operators

### Secondary

-   Hotels
-   Ground Transportation Providers
-   Insurance Providers

## 2.3 User Personas

### Business Traveler

Goals: - Minimize delays - Protect business schedule

Pain Points: - Manual rebooking - Multiple disconnected services

### Leisure Traveler

Goals: - Preserve itinerary - Reduce additional costs

Pain Points: - Confusing policies - Budget uncertainty

### Family Traveler

Goals: - Keep group together - Reduce waiting time

Pain Points: - Coordinating multiple bookings

## 2.4 User Journey

### Existing Workflow

``` text
Flight Cancelled
↓
Search Flights
↓
Call Hotel
↓
Arrange Transport
↓
Estimate Costs
↓
Confirm Everything
```

### TR-OS Workflow

``` text
Flight Cancelled
↓
Recover My Trip
↓
Mission Created
↓
AI Agents Collaborate
↓
Recovery Plan
↓
User Approval
```

## 2.5 Domain Events

Core events:

-   FlightCancelled
-   FlightDelayed
-   GateChanged
-   MissedConnection
-   HotelConflict
-   WeatherAlert

Each event creates or updates a mission.

## 2.6 Functional Requirements

-   Detect disruption
-   Create recovery mission
-   Execute multiple agents
-   Query Atlas APIs
-   Validate policies
-   Produce explainable recommendations

## 2.7 Non-Functional Requirements

-   Scalable
-   Explainable
-   Reliable
-   Extensible
-   Low latency

## 2.8 Success Metrics

Business: - Reduced recovery time - Lower user effort

Technical: - Mission success rate - Agent completion rate - API success
rate

## 2.9 Domain Model

``` text
Traveler
    │
    ▼
Mission
    ├── Flight
    ├── Hotel
    ├── Budget
    ├── Policy
    ├── Transport
    ▼
Recovery Plan
```

Mission is the core business entity.

## Architect's Note

The next chapter defines the overall architecture, architectural
principles, and the rationale for selecting a hybrid supervisor-based
multi-agent design.

---

# Chapter 3 --- Overall System Architecture

------------------------------------------------------------------------

# 3.1 Architectural Philosophy

TR-OS is designed as a **Mission-Oriented Agentic AI Platform**.

Unlike conventional travel applications that execute isolated API
requests, TR-OS treats every disruption as a mission requiring
coordinated reasoning across multiple specialized agents.

The architecture is built around four principles:

-   Mission-first execution
-   Event-driven orchestration
-   Shared state collaboration
-   Explainable reasoning

------------------------------------------------------------------------

# 3.2 Why Not a Traditional Chatbot?

Traditional chatbot architecture:

``` text
User
  │
  ▼
LLM
  │
  ▼
Answer
```

Limitations:

-   Single reasoning context
-   Poor task specialization
-   Difficult to validate
-   Limited explainability

TR-OS instead separates responsibilities among autonomous agents.

------------------------------------------------------------------------

# 3.3 High-Level Architecture

``` text
Traveler
    │
    ▼
Frontend (React)
    │
    ▼
Backend API
    │
    ▼
Mission Engine
    │
    ▼
Mission Graph
    │
    ▼
Supervisor Agent
    │
    ▼
Shared Mission State
    │
 ┌──┼───────────────┐
 ▼  ▼       ▼       ▼
Flight  Hotel  Budget  Policy
Agent   Agent  Agent   Agent
 │       │       │       │
 └───────┴───────┴───────┘
            │
            ▼
      Critic Agent
            │
            ▼
    Reflection Agent
            │
            ▼
      Summary Agent
            │
            ▼
 Recovery Recommendation
```

------------------------------------------------------------------------

# 3.4 Mission Engine

The Mission Engine is the heart of TR-OS.

Responsibilities:

-   Receive travel events
-   Create missions
-   Track mission lifecycle
-   Invoke supervisor
-   Persist mission state
-   Monitor completion

Every disruption becomes an executable mission.

Example:

``` text
FlightCancelled
        │
        ▼
Mission Created
```

------------------------------------------------------------------------

# 3.5 Mission Lifecycle

``` text
Created
   │
   ▼
Context Collection
   │
   ▼
Planning
   │
   ▼
Parallel Agent Execution
   │
   ▼
Validation
   │
   ▼
Reflection
   │
   ▼
Recommendation
   │
   ▼
Completed
```

------------------------------------------------------------------------

# 3.6 Event-Driven Design

Core events include:

-   FlightCancelled
-   FlightDelayed
-   MissedConnection
-   WeatherAlert
-   HotelConflict

Each event is transformed into a mission instead of directly invoking an
LLM.

------------------------------------------------------------------------

# 3.7 Shared Mission State

All agents collaborate through a shared state.

Example attributes:

-   Mission ID
-   Flight Details
-   Hotel Details
-   Budget
-   ETA
-   User Preferences
-   Agent Outputs

Agents communicate indirectly by reading and updating this state.

------------------------------------------------------------------------

# 3.8 Architectural Decisions

## ADR-001

Use a Supervisor Agent.

Reason:

Centralized orchestration and simplified coordination.

------------------------------------------------------------------------

## ADR-002

Use Shared Mission State.

Reason:

Avoid direct peer-to-peer coupling between agents.

------------------------------------------------------------------------

## ADR-003

Use ReAct for every tool-enabled agent.

Reason:

Transparent reasoning and better recovery from incomplete information.

------------------------------------------------------------------------

## ADR-004

Introduce Reflection Agent.

Reason:

Validate and improve recommendations before presenting them to users.

------------------------------------------------------------------------

# 3.9 Scalability

The architecture supports future agents without redesign.

Examples:

-   Visa Agent
-   Insurance Agent
-   Currency Agent
-   Emergency Agent
-   Local Event Agent

New agents subscribe to the mission state and participate in future
workflows.

------------------------------------------------------------------------

# 3.10 Architect's Note

Chapter 4 will define the internal multi-agent orchestration model,
including supervisor logic, execution graph, communication strategy, and
the detailed responsibilities of every agent.

---

# Chapter 4 --- Multi-Agent Orchestration Architecture

------------------------------------------------------------------------

# 4.1 Purpose

The objective of this chapter is to define how autonomous agents
collaborate to complete a travel recovery mission.

TR-OS does not execute a single prompt through one LLM. Instead, it
decomposes a mission into specialized tasks executed by independent
agents coordinated through a Supervisor and a Shared Mission State.

------------------------------------------------------------------------

# 4.2 Why Multi-Agent?

A flight disruption affects multiple business domains simultaneously:

-   Flight availability
-   Airline policies
-   Hotel reservations
-   Ground transportation
-   Budget
-   Weather

A monolithic prompt becomes difficult to validate and explain.

Therefore TR-OS adopts specialization.

------------------------------------------------------------------------

# 4.3 Architectural Style

TR-OS uses a **Hybrid Supervisor Architecture**.

Characteristics:

-   Central Supervisor
-   Shared Blackboard Memory
-   Parallel specialist agents
-   Reflection stage
-   Critic validation

It is intentionally **not** a pure swarm.

Reason: Travel recovery contains strong dependencies (e.g. hotel updates
depend on arrival time). Central orchestration reduces conflicts while
preserving parallel execution.

------------------------------------------------------------------------

# 4.4 Agent Runtime

``` text
Mission Engine
      │
      ▼
Supervisor
      │
      ▼
Shared Mission State
      │
 ┌────┼─────────────────────────────┐
 ▼    ▼      ▼       ▼      ▼       ▼
Flight Hotel Budget Policy Transport Weather
Agent  Agent Agent  Agent  Agent     Agent
      │
      ▼
Critic
      │
      ▼
Reflection
      │
      ▼
Summary
```

Every agent is stateless.

Mission information lives inside the Shared Mission State.

------------------------------------------------------------------------

# 4.5 Supervisor Agent

Purpose

-   Receive mission
-   Plan execution graph
-   Spawn agents
-   Monitor completion
-   Merge outputs
-   Escalate failures

Inputs

-   Mission ID
-   User profile
-   Trigger event

Outputs

-   Execution graph
-   Mission state updates
-   Final plan

The Supervisor never performs domain reasoning.

Its responsibility is orchestration.

------------------------------------------------------------------------

# 4.6 Shared Mission State

Shared state follows the Blackboard Architecture pattern.

Example schema

``` json
{
  "mission_id": "...",
  "status": "running",
  "flight": {},
  "hotel": {},
  "transport": {},
  "budget": {},
  "preferences": {},
  "agent_outputs": {},
  "confidence": {}
}
```

Rules

-   Agents read current state.
-   Agents write only their assigned outputs.
-   Agents never overwrite another agent's ownership without supervisor
    approval.

Benefits

-   Loose coupling
-   Easier debugging
-   Deterministic execution
-   Replay capability

------------------------------------------------------------------------

# 4.7 Agent Registry

  Agent        Responsibility        Primary Tool
  ------------ --------------------- ---------------------
  Flight       Alternative flights   Atlas Flight API
  Hotel        Accommodation         Atlas Hotel API
  Policy       Airline rules         RAG / KB
  Budget       Cost optimisation     Internal calculator
  Transport    Airport transfer      Maps / Travel API
  Weather      Weather risk          Weather API
  Critic       Validation            LLM
  Reflection   Improvement           LLM
  Summary      User explanation      LLM

The registry enables future agents to be added without redesigning the
runtime.

------------------------------------------------------------------------

# 4.8 Execution Model

## Sequential

``` text
Mission
 ↓
Context
 ↓
Planning
```

## Parallel

``` text
          Shared State
          /  |   |   \
 Flight Hotel Budget Policy
```

Independent agents execute simultaneously.

## Validation

``` text
Parallel Results
      │
      ▼
Critic
      │
      ▼
Reflection
      │
      ▼
Summary
```

------------------------------------------------------------------------

# 4.9 ReAct Inside Each Agent

Every tool-enabled agent follows the same internal loop.

``` text
Thought
   │
   ▼
Action
   │
   ▼
Observation
   │
   ▼
Reason
   │
   ▼
Need More Information?
   │
 ┌─Yes───────────────┐
 ▼                   │
Action Again         │
 └──────────────▲────┘
                │
                No
                │
                ▼
Return Result
```

Example (Flight Agent)

Thought: Need earlier replacement.

Action: Query Atlas Flight API.

Observation: Three routes available.

Reason: Route B has lowest delay.

Return: Best candidate.

------------------------------------------------------------------------

# 4.10 Communication Pattern

Agents never call one another directly.

Instead:

``` text
Flight Agent
      │
      ▼
Shared State
      ▲
      │
Hotel Agent
```

Advantages

-   Decoupling
-   Easier scaling
-   Traceability
-   Replay support

------------------------------------------------------------------------

# 4.11 Failure Handling

If an agent fails:

1.  Retry
2.  Fallback tool (if available)
3.  Return partial output
4.  Notify Supervisor
5.  Continue remaining mission

The entire mission should not fail because a single supporting service
becomes unavailable.

------------------------------------------------------------------------

# 4.12 Reflection Pipeline

Before presenting recommendations:

``` text
Agent Outputs
      │
      ▼
Critic
      │
      ▼
Reflection
      │
      ▼
Improved Recommendation
```

Reflection questions include:

-   Can total cost be reduced?
-   Is arrival time acceptable?
-   Are there hidden conflicts?
-   Is another option objectively better?

------------------------------------------------------------------------

# 4.13 Architectural Decision Records

ADR-005

Decision: Use Blackboard Shared State.

Reason: Avoid peer-to-peer complexity.

ADR-006

Decision: Supervisor owns orchestration.

Reason: Business dependencies require deterministic execution.

ADR-007

Decision: Reflection is mandatory.

Reason: Improve recommendation quality before user approval.

------------------------------------------------------------------------

# 4.14 Future Evolution

The runtime is intentionally extensible.

Future agents:

-   Visa Agent
-   Insurance Agent
-   Currency Agent
-   Baggage Agent
-   Emergency Response Agent
-   Local Event Agent

Each subscribes to the same mission lifecycle.

------------------------------------------------------------------------

# Architect's Note

Chapter 5 will formally specify the ReAct Framework used throughout
TR-OS, including prompt contracts, tool invocation lifecycle, reasoning
templates, confidence scoring, retry policies, and explainability
strategy.

---

# Chapter 5 --- ReAct Reasoning Framework & Agent Execution Specification

------------------------------------------------------------------------

# 5.1 Purpose

This chapter defines the internal reasoning standard used by every
intelligent agent inside TR-OS.

Unlike conventional prompt-response systems, TR-OS requires every
decision-making agent to explicitly reason, interact with external
tools, evaluate observations, and determine whether additional actions
are required before producing a recommendation.

This behaviour is standardized through the ReAct (Reason + Act)
framework.

------------------------------------------------------------------------

# 5.2 Why ReAct?

Traditional prompting:

``` text
Question
    │
    ▼
LLM
    │
    ▼
Answer
```

Problem:

-   Hallucination
-   No external verification
-   No intermediate reasoning
-   Difficult to audit

ReAct introduces an explicit reasoning cycle.

``` text
Thought
    │
    ▼
Action
    │
    ▼
Observation
    │
    ▼
Evaluate
    │
    ▼
Repeat (if required)
```

------------------------------------------------------------------------

# 5.3 TR-OS ReAct Standard

Every tool-enabled agent MUST implement the following execution
lifecycle.

``` mermaid
flowchart TD

A[Receive Mission Context]
-->B[Thought]

B-->C{Need External Information?}

C--Yes-->D[Action]

D-->E[Tool Invocation]

E-->F[Observation]

F-->G[Reason]

G-->C

C--No-->H[Generate Output]

H-->I[Update Shared Mission State]
```

No agent may bypass this lifecycle.

------------------------------------------------------------------------

# 5.4 Execution Contract

Every execution consists of six phases.

## Phase 1 --- Context Loading

Input:

-   Mission
-   Shared State
-   User Preferences
-   Previous Agent Outputs

Output:

Internal Working Context

------------------------------------------------------------------------

## Phase 2 --- Thought

Purpose:

Generate an execution plan.

Example

Thought:

"I need to determine the earliest flight that satisfies budget and
arrival constraints."

Rules

Thoughts are internal.

They are NOT exposed to users.

------------------------------------------------------------------------

## Phase 3 --- Action

The agent determines which tool to invoke.

Example

``` text
Atlas Flight Search

Weather API

Policy Knowledge Base

Maps API
```

Actions must be deterministic.

------------------------------------------------------------------------

## Phase 4 --- Observation

The external tool returns structured information.

Example

``` json
{
  "flight":"SQ318",
  "arrival":"18:35",
  "price":420
}
```

Observations become evidence.

Agents must not invent observations.

------------------------------------------------------------------------

## Phase 5 --- Evaluation

Questions:

-   Is information complete?
-   Are constraints satisfied?
-   Should another search be executed?
-   Is confidence sufficient?

If not,

return to Action.

------------------------------------------------------------------------

## Phase 6 --- Commit

The agent writes structured output into Shared Mission State.

------------------------------------------------------------------------

# 5.5 Agent Output Contract

Every agent returns the same schema.

``` json
{
  "agent":"FlightAgent",
  "status":"completed",
  "confidence":0.92,
  "reasoning_summary":"Earlier arrival with minimal delay.",
  "recommendation":{},
  "evidence":[]
}
```

This standard enables downstream validation.

------------------------------------------------------------------------

# 5.6 Tool Invocation Policy

Every tool invocation records:

-   Tool Name
-   Request Timestamp
-   Latency
-   Success
-   Failure Reason
-   Retry Count

This supports observability and replay.

------------------------------------------------------------------------

# 5.7 Retry Strategy

Retry conditions

-   Timeout
-   Temporary API failure
-   Rate limit

Do NOT retry

-   Invalid request
-   Authentication failure
-   Unsupported destination

Retry Policy

Attempt 1

↓

Retry

↓

Retry

↓

Fallback

↓

Notify Supervisor

------------------------------------------------------------------------

# 5.8 Confidence Scoring

Each recommendation includes confidence.

Example contributors

  Factor                      Weight
  ------------------------- --------
  Data completeness              30%
  API reliability                20%
  Constraint satisfaction        30%
  Critic validation              20%

Final confidence

``` text
0.00 – 0.39 Low

0.40 – 0.69 Medium

0.70 – 1.00 High
```

------------------------------------------------------------------------

# 5.9 Explainability Policy

The system never returns a recommendation without justification.

Minimum explanation:

-   Why selected
-   Alternatives considered
-   Trade-offs
-   Assumptions
-   Confidence

Example

``` text
Selected Flight SQ318 because:

• Earliest arrival
• Within budget
• Compatible hotel check-in
• Lowest disruption score
```

------------------------------------------------------------------------

# 5.10 Reflection Trigger

Reflection is executed when:

-   Confidence below threshold
-   Conflicting agent outputs
-   Multiple equivalent options
-   Missing evidence

Reflection Questions

-   Can cost be reduced?
-   Can delay be reduced?
-   Is another itinerary objectively better?
-   Have all constraints been satisfied?

------------------------------------------------------------------------

# 5.11 Prompt Contract

Each agent prompt follows:

1.  Role
2.  Mission
3.  Constraints
4.  Available Tools
5.  Shared State
6.  Expected JSON Output

No free-form responses are allowed internally.

------------------------------------------------------------------------

# 5.12 Observability

Every execution generates:

-   Trace ID
-   Mission ID
-   Agent ID
-   Execution Duration
-   Tool Calls
-   Retry Count
-   Confidence
-   Final Status

These metrics support debugging and future analytics.

------------------------------------------------------------------------

# 5.13 Architectural Decision Records

ADR-008

Decision: Standardize ReAct lifecycle.

Reason: Consistent behaviour across all agents.

ADR-009

Decision: Require structured outputs.

Reason: Reliable orchestration and downstream validation.

ADR-010

Decision: Separate internal reasoning from user-facing explanations.

Reason: Improve safety, auditability, and maintainability.

------------------------------------------------------------------------

# 5.14 Chapter Summary

The ReAct framework defines the execution contract for every intelligent
agent in TR-OS.

By enforcing a common reasoning lifecycle, structured outputs, tool
invocation policies, and confidence scoring, the platform achieves
transparent, repeatable, and explainable decision making suitable for
mission-critical travel recovery.

------------------------------------------------------------------------

## Architect's Note

The next chapter will specify the Shared Mission State, Blackboard
Architecture, state schema, ownership rules, event propagation, and
inter-agent communication protocol in production-level detail.

---

# Chapter 6 --- Shared Mission State & Blackboard Architecture

------------------------------------------------------------------------

# 6.1 Purpose

The Shared Mission State (SMS) is the single source of truth for every
mission executed inside TR-OS.

Rather than allowing agents to communicate directly, every agent
collaborates through a centralized state repository implementing the
**Blackboard Architecture Pattern**.

This design provides:

-   Loose coupling
-   Deterministic execution
-   Explainability
-   Replayability
-   Scalability

------------------------------------------------------------------------

# 6.2 Why Blackboard Architecture?

Direct agent-to-agent communication creates tightly coupled workflows.

Example:

``` text
Flight Agent
   │
   ├──► Hotel Agent
   ├──► Budget Agent
   ├──► Policy Agent
   └──► Transport Agent
```

Problems:

-   Circular dependencies
-   Difficult debugging
-   Hidden communication paths
-   High maintenance cost

Instead TR-OS adopts:

``` text
                 Shared Mission State
                ┌────────────────────┐
Flight Agent ───►                    │
Hotel Agent  ───►                    │
Budget Agent ──►   BLACKBOARD        │
Policy Agent ──►                    │
Weather Agent ─►                    │
Transport ─────►                    │
                └────────────────────┘
```

Agents never invoke each other directly.

------------------------------------------------------------------------

# 6.3 Design Principles

1.  Single Source of Truth
2.  Immutable mission history
3.  Controlled ownership
4.  Append-over-overwrite
5.  Event-driven updates
6.  Versioned state

------------------------------------------------------------------------

# 6.4 Mission State Lifecycle

``` mermaid
stateDiagram-v2

[*] --> Created
Created --> ContextLoaded
ContextLoaded --> Planning
Planning --> Running
Running --> Validation
Validation --> Reflection
Reflection --> Recommendation
Recommendation --> Completed
Completed --> Archived
```

Each transition generates an event.

------------------------------------------------------------------------

# 6.5 Mission State Schema

``` json
{
  "mission_id":"uuid",
  "version":1,
  "status":"running",
  "trigger_event":"FlightCancelled",
  "traveler":{},
  "flight":{},
  "hotel":{},
  "transport":{},
  "budget":{},
  "preferences":{},
  "agent_outputs":{},
  "recommendation":{},
  "confidence":{},
  "audit":[]
}
```

Mission ID uniquely identifies one recovery workflow.

Version increments after every successful commit.

------------------------------------------------------------------------

# 6.6 Context Schema

Mission Context contains immutable input information.

Example:

``` json
{
  "origin":"KUL",
  "destination":"NRT",
  "traveler_type":"Business",
  "airline":"Malaysia Airlines",
  "booking_reference":"ABC123"
}
```

Context must never be modified by downstream agents.

------------------------------------------------------------------------

# 6.7 Agent Output Schema

Every agent writes using the same contract.

``` json
{
  "agent":"FlightAgent",
  "status":"completed",
  "confidence":0.91,
  "timestamp":"ISO8601",
  "result":{},
  "evidence":[],
  "warnings":[]
}
```

This guarantees interoperability.

------------------------------------------------------------------------

# 6.8 Ownership Matrix

  State            Owner           Read   Write
  ---------------- --------------- ------ ---------------
  Flight           Flight Agent    All    Flight Agent
  Hotel            Hotel Agent     All    Hotel Agent
  Budget           Budget Agent    All    Budget Agent
  Policy           Policy Agent    All    Policy Agent
  Weather          Weather Agent   All    Weather Agent
  Recommendation   Summary Agent   All    Summary Agent

Supervisor may override ownership only during recovery or rollback.

------------------------------------------------------------------------

# 6.9 Read / Write Rules

Rules:

-   Read is open.
-   Write is restricted.
-   Delete is prohibited.
-   Historical versions are immutable.

This preserves traceability.

------------------------------------------------------------------------

# 6.10 State Versioning

Each successful update increments the version.

Example

``` text
Version 1
Flight Context

↓

Version 2
Flight Result Added

↓

Version 3
Budget Added

↓

Version 4
Critic Validation

↓

Version 5
Reflection Applied
```

Rollback can return to any stable version.

------------------------------------------------------------------------

# 6.11 Event Propagation

Every state update emits an internal event.

``` text
FlightAgent Updated

↓

State Updated

↓

Mission Event Published

↓

Interested Agents React
```

Example

Flight Agent updates ETA.

Hotel Agent observes new ETA.

Hotel Agent recalculates late check-in.

No direct messaging required.

------------------------------------------------------------------------

# 6.12 Conflict Resolution

Potential conflicts:

-   Budget exceeds limit
-   Hotel unavailable
-   Conflicting arrival times
-   Multiple equally valid flights

Resolution order:

1.  Detect
2.  Flag
3.  Critic evaluates
4.  Reflection improves
5.  Supervisor commits

------------------------------------------------------------------------

# 6.13 Memory Strategy

Three layers:

## Static Memory

Business rules.

## Mission Memory

Current mission state.

## Audit Memory

Historical execution logs.

Future versions may introduce long-term traveler preferences.

------------------------------------------------------------------------

# 6.14 Rollback Strategy

Rollback occurs when:

-   Invalid recommendation
-   Corrupted state
-   Critical tool failure

Supervisor restores the previous stable version.

------------------------------------------------------------------------

# 6.15 Audit Trail

Every write operation records:

-   Mission ID
-   Agent
-   Previous Version
-   New Version
-   Timestamp
-   Change Summary

Audit data supports explainability and debugging.

------------------------------------------------------------------------

# 6.16 Security Considerations

Sensitive fields:

-   Booking reference
-   Passenger information
-   Payment metadata

Requirements:

-   Encrypt at rest
-   Encrypt in transit
-   Least privilege access
-   Redact logs

------------------------------------------------------------------------

# 6.17 Observability

Metrics:

-   State updates/sec
-   Average version count
-   Rollbacks
-   Conflicts detected
-   Conflict resolution time
-   Average mission duration

------------------------------------------------------------------------

# 6.18 Mermaid Sequence Diagram

``` mermaid
sequenceDiagram

participant S as Supervisor
participant F as Flight Agent
participant B as Blackboard
participant H as Hotel Agent

S->>F: Execute
F->>B: Update ETA
B-->>H: State Changed
H->>B: Update Hotel Recommendation
B-->>S: Mission Updated
```

------------------------------------------------------------------------

# 6.19 Architectural Decision Records

### ADR-011

Decision: Adopt Blackboard Architecture.

Reason: Loose coupling and scalable collaboration.

### ADR-012

Decision: Version every mission state.

Reason: Support rollback, replay and auditing.

### ADR-013

Decision: Restrict state ownership.

Reason: Prevent conflicting writes.

### ADR-014

Decision: Append audit history.

Reason: Support explainability and compliance.

------------------------------------------------------------------------

# 6.20 Chapter Summary

The Shared Mission State is the operational backbone of TR-OS. It
enables independent agents to collaborate without direct dependencies,
guarantees deterministic execution through ownership rules and
versioning, and provides a fully auditable history of every decision.
This architecture forms the foundation for reliable orchestration,
explainable AI, and future scalability as new agents and travel services
are introduced.

------------------------------------------------------------------------

## Architect's Note

Chapter 7 will define each production agent individually, including
responsibilities, internal workflow, prompt contracts, tool permissions,
state ownership, error handling, KPIs, and interaction with the Shared
Mission State.

---

# Chapter 7 --- Agent Specifications (Part 1)

**Sections Covered** - 7.0 Agent Runtime - 7.1 Supervisor Agent

------------------------------------------------------------------------

# 7.0 Agent Runtime

## Purpose

The Agent Runtime is the execution environment responsible for
coordinating all intelligent agents during a mission.

It ensures that every mission follows a deterministic lifecycle while
allowing domain-specific agents to execute independently through the
Shared Mission State.

------------------------------------------------------------------------

## Runtime Responsibilities

-   Accept a mission from the Mission Engine.
-   Load mission context.
-   Initialize Shared Mission State.
-   Execute the Supervisor Agent.
-   Coordinate specialist agents.
-   Track execution progress.
-   Trigger validation.
-   Trigger reflection.
-   Produce the final recovery plan.

------------------------------------------------------------------------

## Runtime Lifecycle

``` mermaid
flowchart TD

A[Mission Created]
-->B[Load Context]

B-->C[Supervisor Planning]

C-->D[Spawn Specialist Agents]

D-->E[Parallel Execution]

E-->F[Critic Validation]

F-->G[Reflection]

G-->H[Summary]

H-->I[Mission Completed]
```

------------------------------------------------------------------------

## Runtime Principles

1.  Every mission has one Supervisor.
2.  Agents never communicate directly.
3.  Shared Mission State is the only collaboration layer.
4.  Every recommendation must be validated.
5.  Every decision must be explainable.

------------------------------------------------------------------------

## Runtime Components

  Component              Purpose
  ---------------------- --------------------------
  Mission Engine         Creates missions
  Supervisor             Coordinates execution
  Shared Mission State   Stores mission data
  Specialist Agents      Solve domain tasks
  Critic                 Detects conflicts
  Reflection             Improves recommendations
  Summary                Generates final response

------------------------------------------------------------------------

## Execution Modes

### Sequential

Used when an agent depends on previous outputs.

Example:

``` text
Context
↓
Supervisor
↓
Planning
```

### Parallel

Used when tasks are independent.

``` text
        Shared State
        /   |   \
Flight Hotel Budget
```

------------------------------------------------------------------------

## Runtime Guarantees

-   Deterministic orchestration
-   Structured outputs
-   Replay support
-   Auditability
-   Versioned mission state

------------------------------------------------------------------------

# 7.1 Supervisor Agent

## Purpose

The Supervisor Agent is the orchestration brain of TR-OS.

It does **not** search flights, calculate budgets, or evaluate airline
policies.

Instead, it coordinates specialist agents and ensures that the mission
progresses correctly.

------------------------------------------------------------------------

## Business Responsibility

The Supervisor transforms a travel disruption into an executable
mission.

Example:

``` text
Flight Cancelled

↓

Recover Entire Journey

↓

Delegate Tasks

↓

Merge Results

↓

Return Recovery Plan
```

------------------------------------------------------------------------

## Responsibilities

-   Receive mission.
-   Analyze mission scope.
-   Select required agents.
-   Build execution graph.
-   Monitor progress.
-   Detect failures.
-   Merge outputs.
-   Trigger Critic.
-   Trigger Reflection.
-   Complete mission.

------------------------------------------------------------------------

## Inputs

Supervisor receives:

-   Mission ID
-   Trigger Event
-   Traveler Profile
-   Shared Mission State
-   User Preferences

Example:

``` json
{
  "mission_id":"mission-001",
  "trigger":"FlightCancelled",
  "traveler_type":"Business"
}
```

------------------------------------------------------------------------

## Outputs

The Supervisor never returns user-facing recommendations.

Instead it returns:

``` json
{
  "execution_graph":{},
  "completed_agents":[],
  "failed_agents":[],
  "mission_status":"running"
}
```

------------------------------------------------------------------------

## Internal Workflow

``` mermaid
flowchart TD

A[Receive Mission]
-->B[Analyse Context]

B-->C[Select Agents]

C-->D[Create Execution Graph]

D-->E[Dispatch Agents]

E-->F[Monitor Progress]

F-->G{All Complete?}

G--No-->F

G--Yes-->H[Trigger Critic]

H-->I[Trigger Reflection]

I-->J[Mission Complete]
```

------------------------------------------------------------------------

## Decision Logic

The Supervisor decides:

-   Which agents should execute.
-   Which agents may execute in parallel.
-   Which tasks require sequential execution.
-   When retries should occur.
-   When the mission should terminate.

The Supervisor never performs business reasoning.

------------------------------------------------------------------------

## State Ownership

Reads:

-   Entire Shared Mission State

Writes:

-   Mission Status
-   Execution Graph
-   Runtime Metadata

Never modifies:

-   Flight data
-   Hotel data
-   Budget results

Those belong to specialist agents.

------------------------------------------------------------------------

## Failure Handling

Possible failures:

-   Agent timeout
-   API unavailable
-   Invalid output
-   Missing context

Recovery strategy:

1.  Retry.
2.  Retry alternative tool.
3.  Skip optional task.
4.  Escalate to Critic.
5.  Continue mission.

------------------------------------------------------------------------

## KPIs

-   Mission completion rate
-   Average orchestration latency
-   Parallel execution efficiency
-   Retry frequency
-   Agent success rate

------------------------------------------------------------------------

## Security

The Supervisor never stores:

-   Payment information
-   Passport details
-   Authentication secrets

It only coordinates execution.

------------------------------------------------------------------------

## Architect's Notes

The Supervisor is intentionally lightweight.

Business intelligence belongs to specialist agents, while orchestration
remains centralized. This separation of concerns keeps the runtime
predictable, extensible, and easy to debug.

------------------------------------------------------------------------

## Next Part

Chapter 7 Part 2 covers:

-   Context Agent
-   Flight Agent

These agents introduce the first domain-specific logic and Atlas Travel
API integration.

------------------------------------------------------------------------

------------------------------------------------------------------------

# 7.2 Context Agent

## Purpose

The Context Agent is responsible for transforming raw travel information
into a structured mission context. It establishes the initial state that
all downstream agents rely upon.

Without a complete and consistent context, specialist agents cannot
produce reliable recommendations.

------------------------------------------------------------------------

## Responsibilities

-   Collect traveler profile
-   Validate required information
-   Normalize travel data
-   Extract mission constraints
-   Populate Shared Mission State
-   Identify missing information

------------------------------------------------------------------------

## Inputs

The Context Agent receives:

-   Trigger event
-   Flight booking details
-   Traveler preferences
-   Budget preference
-   Existing itinerary

Example:

``` json
{
  "trigger":"FlightCancelled",
  "booking_reference":"ABC123",
  "origin":"KUL",
  "destination":"NRT",
  "budget":"Medium",
  "traveler_type":"Business"
}
```

------------------------------------------------------------------------

## Outputs

``` json
{
  "mission_context":{
    "origin":"KUL",
    "destination":"NRT",
    "departure_date":"2026-09-12",
    "arrival_constraint":"Before 21:00",
    "budget_limit":800
  },
  "status":"ready"
}
```

------------------------------------------------------------------------

## State Ownership

Owns:

-   Mission Context
-   Traveler Constraints
-   User Preferences

Read Access:

-   All mission metadata

Write Access:

-   Context section only

------------------------------------------------------------------------

## Validation Rules

Mandatory fields:

-   Origin
-   Destination
-   Booking reference
-   Trigger event

Optional fields:

-   Seat preference
-   Airline preference
-   Loyalty program
-   Meal preference

If mandatory information is missing, the agent reports an incomplete
context to the Supervisor.

------------------------------------------------------------------------

## Internal Workflow

``` mermaid
flowchart TD

A[Receive Raw Input]
-->B[Validate Required Fields]
-->C[Normalize Data]
-->D[Extract Constraints]
-->E[Update Shared Mission State]
-->F[Notify Supervisor]
```

------------------------------------------------------------------------

## Failure Modes

-   Missing booking reference
-   Invalid airport code
-   Unsupported route
-   Incomplete traveler profile

Retry is not applicable. User intervention is required.

------------------------------------------------------------------------

## KPIs

-   Context completeness
-   Validation accuracy
-   Initialization latency

------------------------------------------------------------------------

# 7.3 Flight Agent

## Purpose

The Flight Agent identifies and evaluates alternative flight options
after a disruption. It is the primary consumer of Atlas Travel APIs and
is responsible for generating candidate recovery flights.

The Flight Agent **does not** make the final decision. It proposes
ranked options supported by evidence.

------------------------------------------------------------------------

## Responsibilities

-   Search alternative flights
-   Filter invalid routes
-   Rank candidates
-   Estimate arrival impact
-   Publish flight recommendations

------------------------------------------------------------------------

## Primary Tool

Atlas Travel Flight Search API

Future integrations may include airline-specific APIs if available.

------------------------------------------------------------------------

## Inputs

-   Mission Context
-   Original itinerary
-   Budget constraints
-   Arrival constraints
-   User airline preferences

------------------------------------------------------------------------

## Outputs

``` json
{
  "agent":"FlightAgent",
  "status":"completed",
  "candidates":[
    {
      "flight":"SQ318",
      "price":420,
      "arrival":"18:35",
      "score":92
    }
  ],
  "confidence":0.93
}
```

------------------------------------------------------------------------

## Flight Evaluation Criteria

  Criterion            Description
  -------------------- ---------------------------------------
  Arrival Time         Earlier is preferred
  Price                Lower additional cost
  Number of Stops      Fewer stops preferred
  Total Delay          Minimize disruption
  Airline Preference   Respect user preference when possible

------------------------------------------------------------------------

## Ranking Strategy

Each candidate receives a composite score.

Example weighting:

-   Arrival Time: 35%
-   Cost: 25%
-   Delay: 20%
-   Stops: 10%
-   Preference Match: 10%

The highest score becomes the recommended candidate submitted to the
Critic Agent.

------------------------------------------------------------------------

## ReAct Execution

``` mermaid
flowchart TD

A[Load Mission Context]
-->B[Thought]

B-->C[Search Atlas Flight API]

C-->D[Receive Results]

D-->E[Filter Invalid Flights]

E-->F[Rank Candidates]

F-->G{Need Another Search?}

G--Yes-->C
G--No-->H[Publish Result]
```

------------------------------------------------------------------------

## Tool Invocation Contract

Input:

``` json
{
  "origin":"KUL",
  "destination":"NRT",
  "departure_date":"2026-09-12"
}
```

Expected response:

-   Available flights
-   Price
-   Duration
-   Stops
-   Estimated arrival

------------------------------------------------------------------------

## State Ownership

Owns:

-   Flight Recommendations
-   Candidate Rankings

Reads:

-   Mission Context
-   Budget Constraints
-   Traveler Preferences

Never modifies:

-   Hotel
-   Budget
-   Policy
-   Transport

------------------------------------------------------------------------

## Failure Modes

-   Atlas API timeout
-   Empty search results
-   Invalid API response
-   Rate limiting

Recovery Strategy:

1.  Retry request
2.  Reduce search constraints
3.  Return partial candidates
4.  Notify Supervisor

------------------------------------------------------------------------

## KPIs

-   Search latency
-   Successful API calls
-   Candidate quality
-   Average recommendation confidence

------------------------------------------------------------------------

## Security Considerations

The Flight Agent must never persist API credentials within the Shared
Mission State. Credentials remain managed by the backend runtime.

------------------------------------------------------------------------

## Sequence Diagram

``` mermaid
sequenceDiagram
participant S as Supervisor
participant F as Flight Agent
participant A as Atlas API
participant B as Blackboard

S->>F: Execute
F->>A: Search Flights
A-->>F: Candidate Flights
F->>B: Ranked Candidates
B-->>S: Flight Results Ready
```

------------------------------------------------------------------------

## Architect's Note

The Flight Agent produces ranked evidence, not final decisions. Final
recommendations emerge only after Budget, Policy, Hotel, and Critic
agents have completed their analyses.

------------------------------------------------------------------------

## Next Part

Chapter 7 Part 3 covers:

-   Hotel Agent
-   Budget Agent
-   Policy Agent

------------------------------------------------------------------------

------------------------------------------------------------------------

# 7.4 Hotel Agent

## Purpose

The Hotel Agent evaluates how a flight disruption affects accommodation
bookings and produces recovery options that align with the updated
itinerary.

It ensures that lodging remains compatible with the revised arrival
schedule.

## Responsibilities

-   Validate current hotel booking
-   Check late check-in compatibility
-   Determine if booking extension is required
-   Recommend alternative accommodation when necessary
-   Estimate hotel-related recovery costs

## Inputs

-   Updated arrival time
-   Existing hotel reservation
-   Traveler preferences
-   Budget constraints

## Outputs

``` json
{
  "agent":"HotelAgent",
  "status":"completed",
  "recommendation":{
    "action":"Late Check-in",
    "additional_cost":0
  },
  "confidence":0.90
}
```

## Decision Logic

Priority order:

1.  Preserve existing reservation
2.  Enable late check-in
3.  Extend reservation
4.  Recommend nearby replacement

## State Ownership

Owns: - Hotel Recommendation - Accommodation Cost

Reads: - Flight ETA - Mission Context - Budget

## ReAct Workflow

``` mermaid
flowchart TD
A[Read Updated ETA]
-->B[Check Existing Booking]
-->C{Compatible?}
C--Yes-->D[Confirm Booking]
C--No-->E[Search Alternatives]
E-->F[Rank Hotels]
F-->G[Publish Result]
```

## Failure Modes

-   Hotel API unavailable
-   Reservation not found
-   No rooms available

Recovery: - Retry - Recommend manual confirmation - Notify Supervisor

## KPIs

-   Reservation preservation rate
-   Recovery latency
-   Hotel recommendation confidence

------------------------------------------------------------------------

# 7.5 Budget Agent

## Purpose

The Budget Agent evaluates the financial impact of the recovery mission
and recommends options that minimize total disruption cost.

Unlike the Flight Agent, it considers the entire journey.

## Responsibilities

-   Calculate additional airfare
-   Calculate hotel impact
-   Calculate transport impact
-   Estimate total recovery cost
-   Compare candidate plans

## Inputs

-   Flight candidates
-   Hotel recommendation
-   Transport estimate
-   User budget limit

## Outputs

``` json
{
  "agent":"BudgetAgent",
  "recommended_plan":"Option_B",
  "total_cost":685,
  "confidence":0.95
}
```

## Cost Components

  Component       Description
  --------------- --------------------------------
  Flight          Fare difference
  Hotel           Extension or replacement
  Transport       Airport transfer
  Miscellaneous   Additional disruption expenses

## Optimization Strategy

The Budget Agent attempts to:

-   Minimize total cost
-   Respect user budget
-   Preserve itinerary quality

Lower cost alone does not guarantee selection if it introduces
unacceptable delays.

## State Ownership

Owns: - Budget Summary - Cost Comparison - Cost Breakdown

Reads: - Flight - Hotel - Transport

## ReAct Workflow

``` mermaid
flowchart TD
A[Collect Costs]
-->B[Calculate Totals]
-->C[Compare Plans]
-->D[Rank Options]
-->E[Publish Budget Report]
```

## Failure Modes

-   Missing price information
-   Currency conversion unavailable

Fallback: - Estimate using available values - Flag reduced confidence

## KPIs

-   Cost estimation accuracy
-   Processing latency
-   Budget compliance rate

------------------------------------------------------------------------

# 7.6 Policy Agent

## Purpose

The Policy Agent interprets airline policies and determines whether
travelers are eligible for refunds, compensation, or alternative
services.

## Responsibilities

-   Retrieve airline rules
-   Identify fare restrictions
-   Evaluate refund eligibility
-   Evaluate compensation eligibility
-   Publish policy summary

## Inputs

-   Airline
-   Fare type
-   Booking reference
-   Trigger event

## Outputs

``` json
{
  "agent":"PolicyAgent",
  "refund":true,
  "compensation":"Meal Voucher",
  "confidence":0.88
}
```

## Knowledge Source

Primary: - Airline policy knowledge base - RAG documents

Future: - Official airline APIs

## Decision Rules

Questions evaluated:

-   Is the ticket refundable?
-   Does the delay qualify for compensation?
-   Are free rebooking options available?

## State Ownership

Owns: - Policy Summary - Eligibility Results

Reads: - Mission Context - Flight Details

## ReAct Workflow

``` mermaid
flowchart TD
A[Load Airline Rules]
-->B[Match Fare Type]
-->C[Evaluate Eligibility]
-->D[Generate Policy Summary]
-->E[Update Shared State]
```

## Failure Modes

-   Missing policy
-   Ambiguous fare class
-   Unsupported airline

Recovery: - Return partial guidance - Lower confidence - Notify
Supervisor

## KPIs

-   Policy lookup success
-   Eligibility accuracy
-   Response latency

------------------------------------------------------------------------

## Interaction Summary

``` text
Flight Agent
      │
      ▼
Hotel Agent
      │
      ▼
Budget Agent
      ▲
      │
Policy Agent
```

These agents operate independently through the Shared Mission State and
never communicate directly.

------------------------------------------------------------------------

## Architect's Note

The next part introduces the operational support agents responsible for
transportation planning, weather awareness, mission validation, and
quality assurance before the recommendation reaches the traveler.

------------------------------------------------------------------------

------------------------------------------------------------------------

# 7.7 Transport Agent

## Purpose

The Transport Agent ensures that ground transportation remains
synchronized with the updated travel itinerary after a disruption.

While the Flight Agent focuses on air travel, the Transport Agent
manages the "last-mile" journey between airports, hotels, and
destinations.

------------------------------------------------------------------------

## Responsibilities

-   Recalculate airport transfer
-   Estimate travel duration
-   Detect transfer conflicts
-   Recommend alternative transport
-   Estimate transportation cost

------------------------------------------------------------------------

## Inputs

-   Updated arrival time
-   Arrival airport
-   Hotel location
-   Traveler preferences
-   Budget constraints

------------------------------------------------------------------------

## Outputs

``` json
{
  "agent":"TransportAgent",
  "transport_mode":"Airport Train",
  "estimated_cost":35,
  "estimated_duration":"42 minutes",
  "confidence":0.91
}
```

------------------------------------------------------------------------

## Decision Strategy

Priority:

1.  Existing transport remains valid
2.  Lowest travel time
3.  Reliable transport
4.  Lowest additional cost

------------------------------------------------------------------------

## Tool Permissions

Primary:

-   Maps API
-   Transport API

Future:

-   Ride-hailing APIs
-   Airport shuttle APIs

------------------------------------------------------------------------

## State Ownership

Owns:

-   Transport Recommendation
-   Transport Cost
-   Estimated Arrival

Reads:

-   Flight ETA
-   Hotel Recommendation
-   Mission Context

------------------------------------------------------------------------

## ReAct Workflow

``` mermaid
flowchart TD
A[Read Updated ETA]
-->B[Search Available Transport]
-->C[Estimate Travel Time]
-->D[Compare Options]
-->E[Publish Recommendation]
```

------------------------------------------------------------------------

## Failure Modes

-   Route unavailable
-   Maps API timeout
-   Unsupported destination

Fallback:

-   Recommend taxi
-   Notify Supervisor
-   Lower confidence score

------------------------------------------------------------------------

## KPIs

-   Route accuracy
-   ETA estimation accuracy
-   Transport recommendation latency

------------------------------------------------------------------------

# 7.8 Weather Agent

## Purpose

The Weather Agent evaluates environmental conditions that may affect the
recovery plan.

Its role is advisory. It does not modify bookings but provides
contextual risk information to other agents.

------------------------------------------------------------------------

## Responsibilities

-   Retrieve weather forecast
-   Detect severe weather
-   Estimate operational impact
-   Flag weather-related risks

------------------------------------------------------------------------

## Inputs

-   Destination
-   Departure date
-   Arrival date

------------------------------------------------------------------------

## Outputs

``` json
{
  "agent":"WeatherAgent",
  "risk":"Medium",
  "forecast":"Heavy Rain",
  "confidence":0.89
}
```

------------------------------------------------------------------------

## Decision Rules

Examples:

-   Thunderstorm → Increased delay risk
-   Snow → Transport disruption
-   Typhoon → High operational risk

------------------------------------------------------------------------

## State Ownership

Owns:

-   Weather Summary
-   Risk Level

Reads:

-   Mission Context
-   Flight Recommendation

------------------------------------------------------------------------

## ReAct Workflow

``` mermaid
flowchart TD
A[Load Mission Context]
-->B[Query Weather API]
-->C[Evaluate Risk]
-->D[Publish Weather Summary]
```

------------------------------------------------------------------------

## Failure Modes

-   Weather API unavailable
-   Forecast unavailable

Recovery:

-   Return "Unknown Risk"
-   Notify Supervisor

------------------------------------------------------------------------

## KPIs

-   Forecast retrieval success
-   Weather response latency
-   Risk classification accuracy

------------------------------------------------------------------------

# 7.9 Critic Agent

## Purpose

The Critic Agent performs the final technical validation before
recommendations proceed to the Reflection Agent.

Unlike specialist agents, it does not create new recommendations. It
evaluates whether existing recommendations are logically consistent.

------------------------------------------------------------------------

## Responsibilities

-   Detect conflicts
-   Validate mission completeness
-   Identify inconsistencies
-   Verify evidence
-   Flag low-confidence outputs

------------------------------------------------------------------------

## Inputs

-   Flight Recommendation
-   Hotel Recommendation
-   Budget Report
-   Policy Summary
-   Transport Recommendation
-   Weather Summary

------------------------------------------------------------------------

## Outputs

``` json
{
  "agent":"CriticAgent",
  "status":"validated",
  "issues":[
    "Budget exceeds limit"
  ],
  "confidence":0.94
}
```

------------------------------------------------------------------------

## Validation Checklist

The Critic verifies:

-   Arrival before hotel check-in
-   Budget within limits
-   Transport available
-   Airline policy compatible
-   Required evidence present
-   Confidence above threshold

------------------------------------------------------------------------

## Decision Logic

``` mermaid
flowchart TD
A[Load Agent Outputs]
-->B[Check Completeness]
-->C[Detect Conflicts]
-->D{Critical Issue?}
D--Yes-->E[Flag Reflection]
D--No-->F[Approve Mission]
```

------------------------------------------------------------------------

## State Ownership

Owns:

-   Validation Report
-   Conflict List

Reads:

-   Entire Shared Mission State

Never modifies specialist agent outputs.

------------------------------------------------------------------------

## Conflict Types

-   Time conflict
-   Budget conflict
-   Missing evidence
-   Missing recommendation
-   Incompatible itinerary

------------------------------------------------------------------------

## Failure Modes

-   Missing agent output
-   Invalid schema
-   Corrupted shared state

Recovery:

1.  Notify Supervisor
2.  Request re-execution
3.  Escalate to Reflection if partial validation is possible

------------------------------------------------------------------------

## KPIs

-   Conflict detection rate
-   False positive rate
-   Validation latency
-   Mission approval rate

------------------------------------------------------------------------

## Security

The Critic has read-only access to mission data and cannot modify
specialist recommendations.

------------------------------------------------------------------------

## Interaction Summary

``` text
Flight
  │
Hotel
  │
Budget
  │
Policy
  │
Transport
  │
Weather
  │
  ▼
Critic
```

The Critic consolidates and validates all upstream outputs before
handing the mission to the Reflection Agent.

------------------------------------------------------------------------

## Architect's Note

The final part of Chapter 7 introduces the Reflection Agent and Summary
Agent, which transform validated technical outputs into an optimized,
explainable recovery recommendation suitable for end users.

------------------------------------------------------------------------

Flow

------------------------------------------------------------------------

# 7.10 Reflection Agent

## Purpose

The Reflection Agent performs a final optimization pass after the Critic
Agent has validated the recovery plan. Rather than identifying errors,
it asks whether the validated plan can be improved while still
satisfying mission constraints.

The Reflection Agent improves recommendation quality before it reaches
the traveler.

------------------------------------------------------------------------

## Responsibilities

-   Review validated recommendations
-   Compare alternative recovery paths
-   Improve mission quality
-   Increase recommendation confidence
-   Produce optimization notes

------------------------------------------------------------------------

## Inputs

-   Critic validation report
-   Flight recommendation
-   Hotel recommendation
-   Budget summary
-   Policy summary
-   Transport recommendation
-   Weather summary

------------------------------------------------------------------------

## Outputs

``` json
{
  "agent":"ReflectionAgent",
  "status":"completed",
  "changes":[
    "Selected earlier arrival",
    "Reduced recovery cost by RM45"
  ],
  "confidence":0.97
}
```

------------------------------------------------------------------------

## Reflection Questions

The Reflection Agent evaluates:

-   Can arrival time be improved?
-   Can cost be reduced?
-   Can traveler inconvenience be minimized?
-   Is another option objectively better?
-   Are all traveler constraints satisfied?

------------------------------------------------------------------------

## Decision Strategy

Priority order:

1.  Preserve mission objectives
2.  Reduce disruption
3.  Reduce cost
4.  Improve traveler experience
5.  Increase confidence

------------------------------------------------------------------------

## State Ownership

Owns:

-   Reflection Report
-   Optimization Notes
-   Updated Confidence

Reads:

-   Entire validated mission state

------------------------------------------------------------------------

## ReAct Workflow

``` mermaid
flowchart TD

A[Load Validated Mission]
-->B[Evaluate Alternatives]
-->C{Better Plan Exists?}

C--Yes-->D[Update Recommendation]
C--No-->E[Keep Existing Plan]

D-->F[Publish Reflection Report]
E-->F
```

------------------------------------------------------------------------

## Failure Modes

-   Incomplete validation report
-   Missing recommendation
-   Conflicting optimization goals

Recovery:

-   Preserve existing validated plan
-   Notify Supervisor
-   Reduce confidence

------------------------------------------------------------------------

## KPIs

-   Optimization success rate
-   Average cost reduction
-   Average delay reduction
-   Confidence improvement

------------------------------------------------------------------------

# 7.11 Summary Agent

## Purpose

The Summary Agent transforms structured technical outputs into an
understandable recovery plan for the traveler.

It is the only agent responsible for producing user-facing explanations.

------------------------------------------------------------------------

## Responsibilities

-   Merge validated outputs
-   Generate recovery summary
-   Produce timeline
-   Explain reasoning
-   Present confidence level

------------------------------------------------------------------------

## Inputs

-   Reflection report
-   Flight recommendation
-   Hotel recommendation
-   Budget summary
-   Policy summary
-   Transport recommendation
-   Weather summary

------------------------------------------------------------------------

## Outputs

``` json
{
  "title":"Trip Recovery Plan",
  "flight":"SQ318",
  "hotel":"Late Check-in Approved",
  "transport":"Airport Train",
  "cost":"RM685",
  "confidence":0.97
}
```

------------------------------------------------------------------------

## Explanation Policy

Every recommendation should explain:

-   What changed
-   Why it changed
-   Expected impact
-   Confidence level

Example:

``` text
Your original flight was cancelled.

A replacement flight has been selected because it provides the earliest arrival while remaining within your budget.

Your hotel supports late check-in and your airport transfer has been updated automatically.

Estimated additional cost: RM85.
```

------------------------------------------------------------------------

## State Ownership

Owns:

-   Final Recovery Plan
-   User Explanation
-   Mission Summary

Reads:

-   Entire mission state

------------------------------------------------------------------------

## ReAct Workflow

``` mermaid
flowchart TD

A[Read Final Mission State]
-->B[Merge Results]
-->C[Generate Explanation]
-->D[Create Timeline]
-->E[Publish Final Recovery Plan]
```

------------------------------------------------------------------------

## Failure Modes

-   Missing agent output
-   Missing reflection report

Recovery:

-   Generate partial summary
-   Notify Supervisor
-   Mark confidence as reduced

------------------------------------------------------------------------

## KPIs

-   Summary generation latency
-   Completeness score
-   User readability
-   Recommendation acceptance rate

------------------------------------------------------------------------

# Agent Registry

  Agent        Primary Responsibility   State Owner
  ------------ ------------------------ -------------
  Supervisor   Mission orchestration    Runtime
  Context      Mission initialization   Context
  Flight       Flight recovery          Flight
  Hotel        Accommodation recovery   Hotel
  Budget       Cost optimization        Budget
  Policy       Airline rules            Policy
  Transport    Ground transport         Transport
  Weather      Environmental risk       Weather
  Critic       Validation               Validation
  Reflection   Optimization             Reflection
  Summary      User explanation         Final Plan

------------------------------------------------------------------------

# Cross-Agent Responsibility Matrix

  Capability           Responsible Agent
  -------------------- -------------------
  Mission Creation     Supervisor
  Context Collection   Context
  Flight Search        Flight
  Hotel Recovery       Hotel
  Budget Analysis      Budget
  Airline Rules        Policy
  Ground Transport     Transport
  Weather Risk         Weather
  Validation           Critic
  Optimization         Reflection
  User Response        Summary

------------------------------------------------------------------------

# End-to-End Mission Execution

``` mermaid
flowchart LR

A[Flight Cancelled]
-->B[Mission Engine]
-->C[Supervisor]
-->D[Context]

D-->E[Flight]
D-->F[Hotel]
D-->G[Budget]
D-->H[Policy]
D-->I[Transport]
D-->J[Weather]

E-->K[Critic]
F-->K
G-->K
H-->K
I-->K
J-->K

K-->L[Reflection]
L-->M[Summary]
M-->N[Traveler]
```

------------------------------------------------------------------------

# Chapter 7 Summary

This chapter defines every production agent within TR-OS, including its
responsibilities, ownership, execution workflow, and interaction with
the Shared Mission State.

Together, these agents transform a single travel disruption into a
coordinated recovery mission executed through structured orchestration,
specialized reasoning, validation, optimization, and explainable
recommendations.

The multi-agent architecture enables TR-OS to remain modular,
extensible, and maintainable while supporting future capabilities
without redesigning the core runtime.

------------------------------------------------------------------------

## Architect's Note

The next chapter introduces Atlas Travel API integration, including
endpoint mapping, request/response contracts, authentication flow, error
handling, retry policies, and how each agent invokes external travel
services during mission execution.

---

# Chapter 8 --- Atlas Travel API Integration & External Service Layer

------------------------------------------------------------------------

# 8.1 Purpose

This chapter defines how TR-OS communicates with external travel
services through Atlas Travel APIs. It specifies integration
architecture, authentication, request and response contracts, resiliency
strategies, and security controls.

The objective is to isolate AI agents from provider-specific
implementations while maintaining a consistent internal interface.

------------------------------------------------------------------------

# 8.2 Integration Philosophy

TR-OS adopts the **Adapter Pattern**.

``` text
Flight Agent
      │
      ▼
Flight Service Adapter
      │
      ▼
Atlas Travel API
```

Agents never communicate directly with Atlas APIs. All requests pass
through service adapters.

Benefits:

-   Vendor independence
-   Standardized response format
-   Centralized authentication
-   Simplified testing
-   Easier provider replacement

------------------------------------------------------------------------

# 8.3 Integration Layers

``` mermaid
flowchart TD
A[AI Agent]
-->B[Service Adapter]
B-->C[Authentication Layer]
C-->D[Atlas Travel API]
D-->E[Response Normalizer]
E-->F[Shared Mission State]
```

------------------------------------------------------------------------

# 8.4 Authentication

Authentication is handled exclusively by the backend runtime.

Rules:

-   Agents cannot access API keys.
-   Credentials are injected at runtime.
-   Secrets are never stored in Shared Mission State.

Possible storage:

-   Alibaba Cloud Secrets Manager
-   Environment Variables
-   Future Vault Integration

------------------------------------------------------------------------

# 8.5 Flight Search Service

Consumer:

-   Flight Agent

Purpose:

Retrieve alternative flights after disruption.

Example Request

``` http
GET /flight/search
origin=KUL
destination=NRT
date=2026-09-12
```

Normalized Response

``` json
{
  "flights":[
    {
      "flight_number":"SQ318",
      "departure":"09:30",
      "arrival":"18:35",
      "price":420,
      "stops":0
    }
  ]
}
```

------------------------------------------------------------------------

# 8.6 Hotel Service

Consumer:

-   Hotel Agent

Purpose:

Retrieve accommodation options.

Example Response

``` json
{
  "hotels":[
    {
      "name":"Hilton Tokyo",
      "late_checkin":true,
      "price":180
    }
  ]
}
```

------------------------------------------------------------------------

# 8.7 Transport Service

Consumer:

-   Transport Agent

Returns:

-   Route
-   ETA
-   Estimated Cost
-   Transport Mode

------------------------------------------------------------------------

# 8.8 Request Lifecycle

``` mermaid
sequenceDiagram
participant Agent
participant Adapter
participant Atlas

Agent->>Adapter: Search Request
Adapter->>Atlas: HTTP Request
Atlas-->>Adapter: Response
Adapter-->>Agent: Normalized Result
```

------------------------------------------------------------------------

# 8.9 Response Normalization

Provider-specific fields are converted into TR-OS standard schemas.

Example

Provider:

``` json
{
  "arr_time":"18:35"
}
```

Normalized:

``` json
{
  "arrival_time":"18:35"
}
```

------------------------------------------------------------------------

# 8.10 Retry Policy

Retry:

-   Timeout
-   HTTP 429
-   HTTP 503

Do Not Retry:

-   HTTP 400
-   Authentication Failure
-   Invalid Parameters

Retry Flow

``` text
Attempt
 ↓
Retry
 ↓
Retry
 ↓
Fallback
 ↓
Supervisor
```

------------------------------------------------------------------------

# 8.11 Circuit Breaker

Repeated failures trigger a circuit breaker.

``` text
Failure
 ↓
Failure
 ↓
Failure
 ↓
Circuit Open
 ↓
Cooldown
 ↓
Half Open
 ↓
Recovered
```

------------------------------------------------------------------------

# 8.12 Rate Limiting

The backend enforces:

-   Request quotas
-   Exponential backoff
-   Agent-specific throttling

------------------------------------------------------------------------

# 8.13 Error Taxonomy

Recoverable:

-   Timeout
-   Temporary outage
-   Rate limiting

Non-Recoverable:

-   Invalid credentials
-   Invalid booking
-   Unsupported airport

------------------------------------------------------------------------

# 8.14 Logging

Each request records:

-   Trace ID
-   Mission ID
-   Agent
-   Endpoint
-   Status Code
-   Latency
-   Retry Count

------------------------------------------------------------------------

# 8.15 Security

Requirements:

-   TLS for all requests
-   Secret isolation
-   Least privilege
-   Credential rotation
-   Request validation

Agents never:

-   Store credentials
-   Generate authentication tokens
-   Bypass adapters

------------------------------------------------------------------------

# 8.16 Future Integrations

The adapter layer allows future providers to be integrated without
changing agent logic.

Potential providers:

-   Airline APIs
-   Hotel APIs
-   Ride-hailing APIs
-   Currency APIs
-   Travel Insurance APIs

------------------------------------------------------------------------

# 8.17 Architecture Decision Records

### ADR-015

Decision: Use Adapter Pattern.

Reason: Prevent vendor lock-in.

### ADR-016

Decision: Normalize all provider responses.

Reason: Provide consistent internal schemas.

### ADR-017

Decision: Backend-only authentication.

Reason: Protect secrets and simplify agent implementation.

### ADR-018

Decision: Centralize retry logic.

Reason: Avoid duplicated retry implementations across agents.

------------------------------------------------------------------------

# Chapter Summary

The Atlas Integration Layer separates business reasoning from external
provider communication through adapters, response normalization,
centralized authentication, and resilient networking patterns.

This architecture enables AI agents to remain focused on reasoning while
backend services manage connectivity, security, and fault tolerance.
