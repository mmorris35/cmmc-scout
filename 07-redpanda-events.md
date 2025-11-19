# Redpanda Event Streaming - Compliance Audit Trail

```mermaid
sequenceDiagram
    participant CLI as CMMC Scout
    participant Session as SessionActor
    participant Domain as DomainActor
    participant Scoring as ScoringActor
    participant Redpanda as Redpanda<br/>Topic: assessment.events
    participant Console as Redpanda Console<br/>http://localhost:8080

    CLI->>Session: Start Assessment
    Session->>Redpanda: ✉️ AssessmentStartedEvent
    Note over Redpanda: {<br/>"event_type": "assessment.started",<br/>"assessment_id": "abc-123",<br/>"domain": "Access Control",<br/>"control_count": 4<br/>}

    CLI->>Domain: Evaluate Control AC.L2-3.1.1
    Domain->>Redpanda: ✉️ ControlEvaluatedEvent
    Note over Redpanda: {<br/>"event_type": "control.evaluated",<br/>"control_id": "AC.L2-3.1.1",<br/>"classification": "compliant"<br/>}

    Domain->>Domain: Gap detected (partial compliance)
    Domain->>Redpanda: ✉️ GapIdentifiedEvent
    Note over Redpanda: {<br/>"event_type": "gap.identified",<br/>"control_id": "AC.L2-3.1.2",<br/>"severity": "medium",<br/>"remediation_priority": 5<br/>}

    CLI->>Scoring: Calculate Score
    Scoring->>Session: Complete Assessment
    Session->>Redpanda: ✉️ ReportGeneratedEvent
    Note over Redpanda: {<br/>"event_type": "report.generated",<br/>"compliance_score": 0.75,<br/>"gap_count": 1<br/>}

    Redpanda->>Console: Stream events in real-time
    Console->>Console: Display audit trail
```

## Event Types Emitted

| Event Type | Emitted By | Purpose |
|------------|-----------|---------|
| `assessment.started` | SessionActor | Track when assessments begin |
| `control.evaluated` | DomainActor | Log each control's classification |
| `gap.identified` | DomainActor | Flag non-compliant controls |
| `report.generated` | SessionActor | Record final compliance score |

## Kafka-Compatible Features

- **Topic**: `assessment.events`
- **Partitioning**: By assessment_id for event ordering
- **Retention**: 7 days (configurable)
- **Consumer Groups**: SIEM tools can subscribe
- **Schema Registry**: Available on port 18081
- **Console UI**: http://localhost:8080 for real-time monitoring

## SIEM Integration Ready

Events are JSON-formatted and can be consumed by:
- Splunk via Kafka Connect
- Elasticsearch for log aggregation
- DataDog for security monitoring
- Custom compliance dashboards
