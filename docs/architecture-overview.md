# Manrova Architecture

```mermaid
flowchart TB
    subgraph Sensors["Vessel Telemetry"]
        GPS[GPS]
        Radar[Radar]
        Gyro[Gyro / Speed Log]
    end

    Sensors --> NavAgent["Nav Integrity Agent<br/>(deterministic anomaly check)"]

    NavAgent -->|anomaly found| OOW["Officer of the Watch<br/>(orchestrator)"]

    OOW --> CrewAgent["Crew Readiness Agent"]
    OOW --> PatternAgent["Fleet Pattern Agent"]
    OOW --> ComplianceAgent["Compliance Readiness Agent"]

    CrewAgent --> Fusion["Risk Fusion<br/>(deterministic, weighted)"]
    PatternAgent --> Fusion
    ComplianceAgent --> Fusion
    NavAgent --> Fusion

    Fusion --> Decision{Overall<br/>Severity}
    Decision -->|none / low| Monitor["Continue Monitoring<br/>(no notification)"]
    Decision -->|high / critical| ActionPlan["Prepare Actions<br/>(evidence, notifications)"]

    ActionPlan --> Approval["Human Approval<br/>(Master / DPA / Class Society)"]
    Approval -->|approved| Execute["Execute + Track"]
    Execute --> Resolution["Resolution"]
    Resolution --> Memory["Fleet Memory<br/>(learning for next time)"]
```

## Provider layering

```mermaid
flowchart LR
    Core["Shared Core<br/>core/ · agents/ · oow/ · data/"]
    Core --> AWS["AWS Provider<br/>Strands Agents SDK<br/>(providers/aws/strands/)"]
    Core --> Google["Google Provider<br/>Gemini + ADK + Cloud Run<br/>(providers/google/adk/)"]
    AWS --> Bedrock["Amazon Bedrock<br/>+ AgentCore (optional)"]
    Google --> CloudRun["Google Cloud Run"]
```

`core/`, `agents/`, `oow/` and `data/` are the **shared product core** -
identical business logic for both hackathon submissions. Only
`providers/aws/` and `providers/google/` differ.

## Fallback ASCII version (if Mermaid doesn't render in your viewer)

```
MANROVA
   |
Officer of the Watch (OOW)
   |
   +------------------+------------------+------------------+
   |                  |                  |                  |
Nav Integrity     Crew Readiness     Fleet Pattern      Compliance
   |                  |                  |                  |
   +------------------+------------------+------------------+
                       |
                 Risk Fusion (deterministic)
                       |
          +------------+------------+
          |                         |
     Auto Actions             Human Approval
          |                         |
          +------------+------------+
                       |
                Incident State
                       |
          +------------+------------+
          |                         |
       Memory                Observability
```

## Layering

```
MANROVA CORE  (core/, agents/, oow/, data/)
   |
Provider Interface
   |
   +-----------------------------+-----------------------------+
   |                                                            |
AWS Implementation                                    Google Implementation
   |                                                            |
Strands Agents SDK, AgentCore                         Gemini 3.5+, Google ADK, Google Cloud
```

`core/`, `agents/`, `oow/` and `data/` are the **shared product core** -
identical business logic for both hackathon submissions. Only `providers/aws/`
and `providers/google/` differ.

## Deterministic tools vs. agentic reasoning

Per the build spec, safety-critical math is never delegated to an LLM:

- `agents/nav_integrity/agent.py` - haversine distance, deviation thresholds
- `core/risk/fusion.py` - weighted risk scoring, severity banding
- `core/domain/state_machine.py` - strict incident state transitions

The LLM layer (Strands or Gemini, wired in via `providers/`) sits on top of
these structured outputs to interpret, narrate, and decide next actions - it
never recomputes the numbers itself.

## Where the AWS/Strands and Google/ADK builds plug in

Each specialist agent has a "reasoning seam" comment marking where a real
model call replaces the current deterministic evidence list with an
LLM-refined narrative. The Officer of the Watch's `handle_telemetry` / `approve_and_execute`
flow doesn't change per provider - only how each agent's `.analyze()` /
`.assess()` method is implemented does.

See `providers/aws/strands/README.md` and `providers/google/adk/README.md`
for the provider-specific wiring notes.
