# Claude Code Rules for CMMC Scout

## Project Context

**Project Name:** CMMC Scout
**Type:** AI Agent for CMMC Level 2 Compliance Assessment
**Timeline:** 4-hour hackathon build (AI By the Bay, Nov 18-19, 2025)
**Tech Stack:** Python/FastAPI, LangGraph, Akka, Redpanda, Auth0, Comet
**Target:** Defense contractors needing pre-assessment compliance evaluation

## Core Principles

### 1. Hackathon-Optimized Development
- **Prioritize demo impact over completeness** - Working features beat comprehensive coverage
- **Vendor integrations first** - Akka, Redpanda, Auth0, Comet = 40 bonus points
- **One domain is enough** - Focus on Access Control (22 controls) for demo
- **Functional > Beautiful** - CLI or minimal UI acceptable
- **Early integration testing** - Verify Akka/Redpanda work before building on them

### 2. Security Requirements
- **NO token leakage to LLM** - Auth tokens never in prompts or agent context
- **Input validation** - All user inputs sanitized before LLM processing
- **Prompt injection guards** - System prompts isolated from user content
- **RBAC enforcement** - Auth0 roles: `assessor`, `client`, `admin`
- **Audit everything** - All assessment events to Redpanda for compliance trail
- **Secrets management** - Environment variables only, never hardcoded

### 3. Code Quality Standards

#### Testing (Target: >70% coverage for hackathon)
- **Unit tests required for:**
  - Scoring logic (Red/Yellow/Green classification)
  - Control mapping functions
  - Event emission to Redpanda
- **Integration tests required for:**
  - Auth0 authentication flow
  - Agent conversation state management
  - Report generation
- **Test files:** `tests/test_*.py` matching `src/` structure
- **Run before commits:** `pytest --cov=src --cov-report=term-missing`

#### Code Organization
```
src/
├── main.py                 # FastAPI app, health endpoints
├── auth/
│   ├── auth0_client.py     # Auth0 integration
│   └── middleware.py       # Auth middleware
├── agents/
│   ├── assessment_agent.py # LangGraph agent
│   └── prompts.py          # System prompts (version controlled)
├── actors/
│   ├── session_actor.py    # Akka session management
│   ├── domain_actor.py     # Per-domain assessment
│   └── scoring_actor.py    # Compliance scoring
├── events/
│   ├── redpanda_client.py  # Event producer
│   └── schemas.py          # Event schemas
├── models/
│   ├── database.py         # SQLAlchemy models
│   └── schemas.py          # Pydantic schemas
├── services/
│   ├── control_service.py  # Control data access
│   └── report_service.py   # Gap report generation
└── data/
    └── controls.json       # NIST 800-171 control data
```

#### Python Standards
- **Type hints required** - All function signatures
- **Docstrings for public APIs** - Google style format
- **Line length:** 100 characters max
- **Formatter:** Black (run on save)
- **Linter:** Ruff with strict settings
- **Imports:** Organized by stdlib, third-party, local

### 4. Git Discipline

#### Commit Strategy
- **One semantic commit per subtask** from DEVELOPMENT_PLAN.md
- **Format:** `feat(component): description` or `fix(component): description`
- **Examples:**
  - `feat(auth): integrate Auth0 authentication flow`
  - `feat(agent): implement Access Control domain assessment`
  - `feat(events): add Redpanda event streaming`
  - `fix(scoring): correct partial compliance calculation`

#### Branch Strategy
- **main** - Stable demo-ready code
- **dev** - Integration branch for features
- **Feature branches:** `feature/X.Y.Z-description` matching DEVELOPMENT_PLAN.md task numbers

#### Pre-Commit Hooks
```yaml
- Black formatting
- Ruff linting
- Type checking (mypy)
- Test suite (fast tests only)
```

### 5. Vendor Integration Guidelines

#### Akka (Actor System)
```python
# Use Pykka (Python Akka implementation)
from pykka import ThreadingActor

class SessionActor(ThreadingActor):
    """Manages user assessment session state."""
    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        self.state = {}

    def on_receive(self, message: dict):
        # Handle messages, emit events to Redpanda
        pass
```

**Key Patterns:**
- One SessionActor per user assessment
- DomainActors spawn ControlActors as needed
- Use ask() pattern for scored responses
- Tell pattern for fire-and-forget events

#### Redpanda (Event Streaming)
```python
# Use kafka-python (Redpanda is Kafka-compatible)
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Event schema
{
    "event_type": "control.evaluated",
    "timestamp": "2025-11-18T10:30:00Z",
    "user_id": "user123",
    "assessment_id": "assess456",
    "control_id": "AC.L2-3.1.1",
    "score": "partial",
    "evidence": "Manager approval via email"
}
```

**Topics:**
- `assessment.started`
- `control.evaluated`
- `gap.identified`
- `report.generated`

#### Auth0
```python
# Use authlib
from authlib.integrations.starlette_client import OAuth

# Environment variables required:
# AUTH0_DOMAIN
# AUTH0_CLIENT_ID
# AUTH0_CLIENT_SECRET
# AUTH0_AUDIENCE

# Never pass tokens to LLM - use backend-only validation
```

#### Comet ML
```python
from comet_ml import Experiment

# Track each assessment as an experiment
experiment = Experiment(
    api_key=os.getenv("COMET_API_KEY"),
    project_name="cmmc-scout",
)

# Log prompts, responses, scores, timing
experiment.log_parameters({"domain": "Access Control"})
experiment.log_metrics({"compliance_score": 0.73, "duration_sec": 180})
experiment.log_text("User described email-based approvals...")
```

### 6. LLM Agent Patterns

#### Prompt Structure
```python
SYSTEM_PROMPT = """
You are a CMMC Level 2 assessment agent. Your role is to:
1. Ask specific questions about NIST SP 800-171 controls
2. Evaluate responses as COMPLIANT, PARTIAL, or NON-COMPLIANT
3. Provide clear, actionable remediation guidance
4. Never make assumptions - ask for clarification when uncertain

Current control: {control_id}
Control text: {control_text}
Assessment objective: {assessment_objective}
"""

# User input MUST be validated before inclusion
USER_MESSAGE = f"User response: {sanitize(user_input)}"
```

#### Scoring Logic
```python
def classify_compliance(control_id: str, user_response: str, agent_analysis: str) -> str:
    """
    Returns: 'compliant', 'partial', 'non_compliant'

    Rules:
    - COMPLIANT: Policy exists, documented, evidence available
    - PARTIAL: Policy exists but implementation gaps (audit trail, automation)
    - NON-COMPLIANT: No policy, no process, or critical gaps
    """
    # Use LLM with few-shot examples for consistent classification
    pass
```

### 7. Data Handling

#### Control Data Format
```json
{
  "control_id": "AC.L2-3.1.1",
  "domain": "Access Control",
  "title": "Authorized Access Enforcement",
  "requirement": "Limit system access to authorized users...",
  "assessment_objective": "Determine if the organization has documented policies...",
  "discussion": "Access control policies and procedures...",
  "nist_reference": "NIST SP 800-171 Rev 2"
}
```

#### Database Schema
```python
# SQLAlchemy models
class Assessment(Base):
    id: UUID
    user_id: str
    domain: str
    status: str  # 'in_progress', 'completed'
    score: float
    created_at: datetime

class ControlResponse(Base):
    id: UUID
    assessment_id: UUID
    control_id: str
    user_response: str
    classification: str  # 'compliant', 'partial', 'non_compliant'
    agent_notes: str
    created_at: datetime
```

### 8. Error Handling

```python
# Graceful degradation patterns
try:
    producer.send('assessment.started', event_data)
except KafkaError as e:
    logger.error(f"Redpanda unavailable: {e}")
    # Continue assessment, log locally as fallback
    fallback_log.append(event_data)

# Timeout protection for LLM calls
response = await asyncio.wait_for(
    agent.ask(question),
    timeout=30.0
)

# Session recovery
if session_actor.is_alive():
    session_actor.tell(message)
else:
    # Restart actor, restore from DB
    session_actor = SessionActor.start(user_id)
```

### 9. Demo Preparation Requirements

#### Must Be Visible in Demo
1. **Auth0 login flow** - Show protected route, user profile
2. **Agent conversation** - 3-4 control assessments with scoring
3. **Real-time events** - Redpanda consumer showing events as they happen
4. **Comet dashboard** - Logged prompts and metrics
5. **Gap report** - Generated remediation plan with cost/time estimates

#### Demo Data
- **Pre-seed one user** with partial assessment (resumable)
- **Hardcode sample responses** for consistent demo timing
- **Have backup screenshots** if live demo fails

### 10. Development Workflow

#### Starting a Subtask
```bash
# Example: Starting task 1.2 from DEVELOPMENT_PLAN.md
git checkout -b feature/1.2-redpanda-setup
claude "please re-read claude.md and DEVELOPMENT_PLAN.md, then continue with 1.2"
```

#### Completing a Subtask
1. Run full test suite: `pytest --cov=src`
2. Check coverage: Must be >70%
3. Run linters: `ruff check src/ && black --check src/`
4. Commit with semantic message
5. Update DEVELOPMENT_PLAN.md completion notes
6. Push branch, create PR if collaborative

#### Environment Setup
```bash
# .env file (never commit)
AUTH0_DOMAIN=dev-xxx.us.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx
COMET_API_KEY=xxx
OPENAI_API_KEY=xxx  # or ANTHROPIC_API_KEY
DATABASE_URL=postgresql://localhost/cmmc_scout
REDPANDA_BOOTSTRAP_SERVERS=localhost:9092
```

## Success Metrics

### Functional Requirements
- [ ] User can log in via Auth0
- [ ] Agent conducts assessment for ≥1 domain (Access Control)
- [ ] Scores displayed as Red/Yellow/Green per control
- [ ] Gap report generated with remediation steps
- [ ] All events visible in Redpanda consumer

### Technical Requirements
- [ ] Test coverage >70%
- [ ] All vendor integrations functional
- [ ] No hardcoded secrets
- [ ] Clean `ruff` and `mypy` output
- [ ] Docker Compose starts all services

### Demo Requirements
- [ ] 3-minute video recorded
- [ ] README with setup instructions
- [ ] Devpost submission complete
- [ ] GitHub repo public

## References

- **NIST SP 800-171 Rev 2:** https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final
- **CMMC Model:** https://dodcio.defense.gov/CMMC/
- **Akka (Pykka) Docs:** https://pykka.readthedocs.io/
- **Redpanda Quickstart:** https://docs.redpanda.com/current/get-started/quick-start/
- **Auth0 Python SDK:** https://auth0.com/docs/quickstart/backend/python
- **Comet ML Python:** https://www.comet.com/docs/v2/guides/getting-started/quickstart/

## Notes for Claude Code

When implementing subtasks:
1. **Read this file and DEVELOPMENT_PLAN.md fully** before each session
2. **Ask clarifying questions** if requirements are ambiguous
3. **Write tests first** for scoring and critical logic
4. **Emit events early** - Redpanda integration in first hour
5. **Hardcode sample data** - Don't build admin UIs for control management
6. **Keep it simple** - This is a demo, not a production system
7. **Document assumptions** in code comments
8. **Time-box each subtask** - Move on if stuck >30 minutes

The goal is a **functional demo that scores well on judging criteria**, not a complete product.
