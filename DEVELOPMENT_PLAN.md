# CMMC Scout - Development Plan

## Project Overview

**Goal:** Build a functional AI agent demo that conducts CMMC Level 2 compliance assessments for defense contractors, maximizing hackathon judging score through strategic vendor integrations.

**Timeline:** 4 hours total development time
**Target Score:** 120/100 (base 100 + 20 bonus points)
**Demo Deliverable:** 3-minute video showing complete assessment flow

## Phase 1: Foundation & Infrastructure (60 minutes)

### 1.1 Project Scaffolding and Environment Setup
**Duration:** 20 minutes
**Priority:** CRITICAL

**Deliverables:**
1. Python virtual environment with `requirements.txt` including:
   - `fastapi`, `uvicorn`, `pydantic`
   - `sqlalchemy`, `psycopg2-binary`
   - `pykka` (Akka for Python)
   - `kafka-python` (Redpanda client)
   - `authlib` (Auth0)
   - `comet-ml`
   - `langchain`, `langgraph`, `openai` or `anthropic`
   - `pytest`, `pytest-cov`, `black`, `ruff`, `mypy`
2. `docker-compose.yml` with services:
   - PostgreSQL database
   - Redpanda (Kafka-compatible)
   - Redpanda Console (UI)
3. Basic FastAPI app structure (`src/main.py`) with health endpoint
4. `.env.example` file documenting required environment variables
5. `.gitignore` configured for Python, `.env`, and IDE files
6. Initial git commit

**Completion Notes:**
```
# Verify setup
docker compose up -d
curl http://localhost:8000/health
python -m pytest tests/ --cov
```

---

### 1.2 Redpanda Event Streaming Setup
**Duration:** 20 minutes
**Priority:** CRITICAL (worth 10 bonus points)

**Deliverables:**
1. `src/events/redpanda_client.py` with:
   - `EventProducer` class using kafka-python
   - Connection configuration from environment
   - Graceful fallback if Redpanda unavailable
2. `src/events/schemas.py` defining event types:
   - `AssessmentStartedEvent`
   - `ControlEvaluatedEvent`
   - `GapIdentifiedEvent`
   - `ReportGeneratedEvent`
3. Kafka topics auto-creation on first use
4. Unit tests for event serialization
5. Simple consumer script (`scripts/consume_events.py`) for demo visibility
6. Successfully emit test event to `assessment.test` topic
7. Git commit: `feat(events): add Redpanda event streaming infrastructure`

**Completion Notes:**
```bash
# Verify Redpanda working
docker compose logs redpanda
python scripts/consume_events.py &  # Run in background for demo
# Should see test events in console
```

---

### 1.3 Database Models and Control Data Loading
**Duration:** 20 minutes
**Priority:** HIGH

**Deliverables:**
1. `src/models/database.py` with SQLAlchemy models:
   - `User` (id, auth0_id, email, created_at)
   - `Assessment` (id, user_id, domain, status, score, created_at)
   - `ControlResponse` (id, assessment_id, control_id, classification, user_response, agent_notes)
2. `src/data/controls.json` with Access Control domain controls:
   - Minimum 10 controls from AC.L2-3.1.x series
   - Format: control_id, title, requirement, assessment_objective, discussion
3. `src/services/control_service.py` to load and query control data
4. Database migration/initialization script (`scripts/init_db.py`)
5. Seed one demo user in database
6. Unit tests for control data loading
7. Git commit: `feat(data): add database models and CMMC control data`

**Completion Notes:**
```bash
# Verify database
python scripts/init_db.py
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
# Should have 1 demo user
```

---

## Phase 2: Core Agent & Authentication (90 minutes)

### 2.1 Auth0 Authentication Integration
**Duration:** 25 minutes
**Priority:** CRITICAL (judge sponsor)

**Deliverables:**
1. `src/auth/auth0_client.py` with OAuth configuration
2. `src/auth/middleware.py` for FastAPI route protection
3. FastAPI routes:
   - `GET /auth/login` - Redirect to Auth0
   - `GET /auth/callback` - Handle OAuth callback
   - `GET /auth/user` - Get current user profile (protected)
   - `GET /auth/logout` - Clear session
4. Session management using JWT tokens
5. Role-based access control for `assessor`, `client`, `admin` roles
6. **Security verification:** Token never passed to LLM or logged
7. Simple login test page or CLI flow
8. Git commit: `feat(auth): integrate Auth0 authentication and RBAC`

**Completion Notes:**
```bash
# Manual test or automated
curl -L http://localhost:8000/auth/login
# Follow redirect, verify callback works
# Check token in response
```

---

### 2.2 Akka Actor System for Session Management
**Duration:** 30 minutes
**Priority:** CRITICAL (worth 10 bonus points)

**Deliverables:**
1. `src/actors/session_actor.py` - Manages user assessment session:
   - State: current_domain, current_control_index, responses[]
   - Messages: START_ASSESSMENT, SUBMIT_RESPONSE, GET_STATE
2. `src/actors/domain_actor.py` - Handles domain-specific logic:
   - Loads controls for domain
   - Tracks progress through controls
   - Calculates domain score
3. `src/actors/scoring_actor.py` - Calculates compliance scores:
   - Input: list of control responses
   - Output: compliance_percentage, red/yellow/green counts
4. Actor lifecycle management in FastAPI app
5. Integration with Redpanda (emit events from actors)
6. Unit tests for actor message handling
7. Git commit: `feat(actors): implement Akka actor system for session management`

**Completion Notes:**
```python
# Test actor system
from src.actors.session_actor import SessionActor
actor = SessionActor.start("user123")
response = actor.ask({"type": "START_ASSESSMENT", "domain": "Access Control"})
# Verify state management works
```

---

### 2.3 LLM Assessment Agent Implementation
**Duration:** 35 minutes
**Priority:** CRITICAL

**Deliverables:**
1. `src/agents/prompts.py` with version-controlled prompts:
   - `SYSTEM_PROMPT_TEMPLATE` - Agent role and scoring guidelines
   - `CONTROL_ASSESSMENT_PROMPT` - Per-control question generation
   - `CLASSIFICATION_PROMPT` - Few-shot examples for scoring
2. `src/agents/assessment_agent.py` using LangGraph:
   - State: conversation_history, current_control, user_context
   - Tools: classify_response, ask_followup, mark_complete
   - Safety: input sanitization, prompt injection guards
3. Integration with Comet ML for logging:
   - Log each prompt/response pair
   - Track assessment duration
   - Record classification decisions
4. Conversation flow for 3-4 controls minimum
5. Unit tests with mocked LLM responses
6. Environment variable for LLM provider (OpenAI or Anthropic)
7. Git commit: `feat(agent): implement LangGraph assessment agent with Comet tracking`

**Completion Notes:**
```python
# Test agent conversation
agent = AssessmentAgent(control_id="AC.L2-3.1.1")
response = agent.ask("Do you have an access control policy?")
# Verify Comet experiment logged
```

---

## Phase 3: Assessment Flow & Reporting (60 minutes)

### 3.1 Assessment API Endpoints
**Duration:** 25 minutes
**Priority:** HIGH

**Deliverables:**
1. `POST /api/assessments/start` - Create new assessment:
   - Input: domain name
   - Output: assessment_id, first_question
   - Spawns SessionActor, emits `assessment.started` event
2. `POST /api/assessments/{id}/respond` - Submit control response:
   - Input: user_response text
   - Output: classification, next_question or completion_status
   - Emits `control.evaluated` event
3. `GET /api/assessments/{id}/status` - Get current progress:
   - Returns: controls_completed, current_score, next_control
4. `GET /api/assessments/{id}/report` - Generate gap report
5. Request/response Pydantic models in `src/models/schemas.py`
6. Integration tests for full assessment flow
7. Git commit: `feat(api): add assessment CRUD endpoints`

**Completion Notes:**
```bash
# Test complete flow
curl -X POST http://localhost:8000/api/assessments/start \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"domain": "Access Control"}'
# Verify events in Redpanda console
```

---

### 3.2 Scoring Logic and Gap Identification
**Duration:** 20 minutes
**Priority:** HIGH

**Deliverables:**
1. `src/services/scoring_service.py` with functions:
   - `calculate_domain_score(responses: List[ControlResponse]) -> float`
   - `classify_control(control_id, user_response, agent_analysis) -> str`
   - Traffic light logic: compliant (green), partial (yellow), non_compliant (red)
2. `src/services/gap_service.py`:
   - `identify_gaps(assessment_id) -> List[Gap]`
   - Gap model: control_id, severity, description, remediation_steps
3. Unit tests with known inputs/outputs for scoring consistency
4. Emit `gap.identified` events to Redpanda
5. Documentation of scoring criteria in docstrings
6. Git commit: `feat(scoring): implement compliance scoring and gap identification`

**Completion Notes:**
```python
# Verify scoring logic
from src.services.scoring_service import calculate_domain_score
score = calculate_domain_score(test_responses)
assert 0.0 <= score <= 1.0
```

---

### 3.3 Gap Report Generation
**Duration:** 15 minutes
**Priority:** HIGH

**Deliverables:**
1. `src/services/report_service.py`:
   - `generate_gap_report(assessment_id) -> GapReport`
   - Report includes: executive summary, control-by-control findings, prioritized remediation plan
2. Remediation suggestions with rough cost/time estimates:
   - Low effort: <$5K, <2 weeks
   - Medium effort: $5-20K, 2-8 weeks
   - High effort: >$20K, >8 weeks
3. Export formats: JSON, Markdown (PDF if time permits)
4. Emit `report.generated` event to Redpanda
5. Sample report template with real data
6. Git commit: `feat(reports): add gap report generation with remediation plans`

**Completion Notes:**
```bash
# Generate sample report
python scripts/generate_sample_report.py > demo_report.md
cat demo_report.md  # Verify formatting
```

---

## Phase 4: Demo Preparation & Polish (30 minutes)

### 4.1 Demo Interface and Documentation
**Duration:** 15 minutes
**Priority:** CRITICAL

**Deliverables:**
1. Simple demo interface (choose one):
   - **Option A:** CLI using `typer` or `click` for interactive assessment
   - **Option B:** Minimal web UI with HTML/HTMX (single page)
   - **Option C:** API-only with well-documented cURL examples
2. `README.md` with:
   - Project description and value proposition
   - Architecture diagram (ASCII or embedded image)
   - Quick start instructions (Docker Compose + 3 commands)
   - Environment variable documentation
   - Demo script walkthrough
3. `DEMO.md` with 3-minute presentation script:
   - 0:00-0:30 - Problem and market opportunity
   - 0:30-1:00 - Auth0 login and start assessment
   - 1:00-2:00 - Interactive control assessment (3-4 controls)
   - 2:00-2:30 - Gap report generation
   - 2:30-3:00 - Redpanda events and Comet dashboard
4. Screenshots or GIFs for README
5. Git commit: `docs: add README and demo documentation`

**Completion Notes:**
```bash
# Test full demo flow
./scripts/demo.sh  # Automated demo script
# Time it - should be <3 minutes
```

---

### 4.2 Video Recording and Submission
**Duration:** 15 minutes
**Priority:** CRITICAL

**Deliverables:**
1. Screen recording of 3-minute demo following `DEMO.md` script
2. Voiceover or captions explaining each step
3. Highlight all four vendor integrations visibly:
   - Auth0: Show login redirect
   - Akka: Mention actor system managing state
   - Redpanda: Show event console with real-time events
   - Comet: Show dashboard with logged experiments
4. Video uploaded to YouTube (unlisted) or direct file
5. Devpost submission completed:
   - Title: "CMMC Scout - AI Compliance Assessment Agent"
   - Video link
   - GitHub repo link
   - Description with value prop and technical highlights
6. Final git commit: `chore: finalize demo video and submission`

**Completion Notes:**
```
✅ Video recorded and uploaded
✅ Devpost submitted before deadline (11:00 AM Wednesday)
✅ GitHub repo public and clean
✅ All vendor integrations visible in demo
```

---

## Contingency Plans

### If Running Behind Schedule

**Drop in Priority Order:**
1. **UI/CLI polish** - Use cURL examples instead
2. **Full 10+ controls** - Demo with 3-4 controls only
3. **PDF export** - Markdown report sufficient
4. **Comprehensive tests** - Focus on critical paths only
5. **Multiple domains** - Access Control domain only

### If Vendor Integration Fails

**Akka (Pykka):**
- Fallback: Simple in-memory state management with Python dict
- Still mention "designed for Akka" in presentation
- Document actor pattern in code comments

**Redpanda:**
- Fallback: File-based event logging to `events.jsonl`
- Show file tail in demo instead of Kafka console

**Auth0:**
- Fallback: Mock authentication with hardcoded token
- **Note:** This loses judge points - prioritize fixing this

**Comet:**
- Fallback: Local logging to files
- Show logs in terminal instead of dashboard

---

## Testing Strategy

### Unit Tests (Target: 70% coverage)
- `tests/test_scoring_service.py` - Scoring logic
- `tests/test_control_service.py` - Control data loading
- `tests/test_events.py` - Event serialization
- `tests/test_actors.py` - Actor message handling

### Integration Tests
- `tests/test_assessment_flow.py` - Full assessment cycle
- `tests/test_auth.py` - Auth0 flow (may need mocking)
- `tests/test_agent.py` - Agent conversation (mocked LLM)

### Manual Testing Checklist
- [ ] Docker Compose starts all services
- [ ] Auth0 login redirects correctly
- [ ] Assessment starts and tracks state
- [ ] Agent asks relevant questions
- [ ] Responses classified correctly
- [ ] Events appear in Redpanda console
- [ ] Comet dashboard shows experiments
- [ ] Gap report generates with realistic data
- [ ] Demo runs in <3 minutes

---

## Git Workflow

### Commit Pattern
Each subtask = one semantic commit:
- `1.1` → `feat(init): scaffold project with FastAPI and Docker Compose`
- `1.2` → `feat(events): add Redpanda event streaming infrastructure`
- `1.3` → `feat(data): add database models and CMMC control data`
- `2.1` → `feat(auth): integrate Auth0 authentication and RBAC`
- `2.2` → `feat(actors): implement Akka actor system for session management`
- `2.3` → `feat(agent): implement LangGraph assessment agent with Comet tracking`
- `3.1` → `feat(api): add assessment CRUD endpoints`
- `3.2` → `feat(scoring): implement compliance scoring and gap identification`
- `3.3` → `feat(reports): add gap report generation with remediation plans`
- `4.1` → `docs: add README and demo documentation`
- `4.2` → `chore: finalize demo video and submission`

### Pre-Commit Checklist
```bash
# Before each commit
black src/ tests/
ruff check src/ tests/
mypy src/
pytest --cov=src --cov-report=term-missing
git add .
git commit -m "feat(component): description"
```

---

## Environment Variables Reference

Required in `.env` file:

```bash
# Auth0
AUTH0_DOMAIN=dev-xxx.us.auth0.com
AUTH0_CLIENT_ID=xxx
AUTH0_CLIENT_SECRET=xxx
AUTH0_AUDIENCE=https://cmmc-scout-api

# Comet ML
COMET_API_KEY=xxx
COMET_PROJECT_NAME=cmmc-scout

# LLM Provider (choose one)
OPENAI_API_KEY=sk-xxx
# OR
ANTHROPIC_API_KEY=sk-ant-xxx

# Database
DATABASE_URL=postgresql://cmmc:cmmc@localhost:5432/cmmc_scout

# Redpanda
REDPANDA_BOOTSTRAP_SERVERS=localhost:9092

# App Config
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
```

---

## Success Criteria

### Functional
- ✅ User can authenticate via Auth0
- ✅ Agent conducts assessment for Access Control domain (3+ controls)
- ✅ Responses classified as compliant/partial/non-compliant
- ✅ Gap report generated with remediation suggestions
- ✅ All assessment events visible in Redpanda Console

### Technical
- ✅ Test coverage >70%
- ✅ All four vendor integrations working (Akka, Redpanda, Auth0, Comet)
- ✅ No hardcoded secrets or tokens
- ✅ Clean linter output (ruff, black)
- ✅ Docker Compose starts all services successfully

### Demo & Presentation
- ✅ 3-minute video demonstrating full flow
- ✅ All vendor integrations visible in video
- ✅ Clear value proposition articulated
- ✅ Devpost submission complete before deadline
- ✅ GitHub repo public with comprehensive README

### Judging Criteria Maximization
- **Business Value (20pts):** Defense contractor pain point, clear $50K+ savings
- **Production Readiness (20pts):** Error handling, state recovery, audit logging
- **Security (20pts):** Auth0 RBAC, token handling, input validation
- **Observability (20pts):** Comet tracking, Redpanda audit trail, health endpoints
- **Knowledge & Reasoning (15pts):** NIST 800-171 control mappings, gap analysis
- **Bonus: Akka (+10pts):** Actor system for session management
- **Bonus: Redpanda (+10pts):** Event streaming for compliance audit
- **Bonus: Multi-Agent (+5pts):** Validator agent reviews assessments (stretch goal)

**Target Score: 110-120 points**

---

## Post-Hackathon Roadmap (Optional)

If continuing development:
1. Expand to all 14 domains (110 controls)
2. Evidence upload and document parsing
3. POA&M generation in C3PAO format
4. Multi-user collaboration features
5. Integration with Azure/M365 for automated evidence collection
6. Fine-tune LLM on validated assessment data
7. Mobile app for on-site assessments

---

## Notes for Claude Code

### Starting Each Session
```
Please re-read claude.md and DEVELOPMENT_PLAN.md (entire documents for context),
then continue with [X.Y]
```

### Asking for Help
If stuck on vendor integration:
- **Akka:** Hugh McKee at booth
- **Redpanda:** Chandler Mayo at booth
- **Auth0:** Fred Patton (judge)
- **Comet:** Claire Longo (judge)

### Time Management
- **Set 30-minute alarms per subtask**
- If blocked, move to next task and return later
- Prioritize demo impact over completeness
- **Integration risk items first** (Akka, Redpanda in Phase 1-2)

### Demo Mindset
This is a **proof of concept**, not production software. Focus on:
- **"Wow" factor** - Show all four vendor logos/integrations
- **Clear narrative** - Defense contractor saves $50K
- **Working software** - Even if only 3 controls, make it smooth

Good luck! 🚀
