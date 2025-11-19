# CMMC Scout

> **AI-powered CMMC Level 2 compliance assessment agent for defense contractors**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AI By the Bay Hackathon** | November 18-19, 2025

---

## The Problem

Defense contractors pursuing CMMC Level 2 certification face a **complex, expensive assessment process**:

- 📊 **110 controls** across 14 security domains (NIST SP 800-171)
- 💰 **$50K+ cost** for formal C3PAO assessment
- ⏱️ **Months of preparation** without knowing where they stand
- 🎯 **30% failure rate** on first assessment attempt = $15-30K wasted

Most small to mid-size contractors don't know their compliance posture until they pay for the formal assessment.

## The Solution

**CMMC Scout** is an AI agent that conducts interactive compliance assessments, providing:

✅ **Pre-assessment evaluation** - Know your compliance posture before paying for C3PAO
✅ **Gap identification** - Pinpoint exactly which controls you're failing
✅ **Prioritized remediation** - Cost and time estimates for each fix
✅ **Audit trail** - Complete event log for compliance documentation

### Business Value

- **For Contractors:** Save $50K+ by identifying gaps before formal assessment
- **For Consultants:** White-label assessment tool for client pre-screening
- **For MSPs:** Scalable compliance assessment across multiple clients
- **Market:** $500-2000/month per contractor SaaS potential

---

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Auth0/Okta    │────▶│  Assessment  │────▶│   Redpanda  │
│  (AuthN/AuthZ)  │     │    Agent     │     │ (Event Bus) │
└─────────────────┘     └──────┬───────┘     └──────┬──────┘
                               │                    │
                               ▼                    ▼
                        ┌──────────────┐     ┌─────────────┐
                        │     Akka     │     │    Comet    │
                        │ (Orchestrator)│     │ (Observability)│
                        └──────────────┘     └─────────────┘
```

### Technology Stack

| Component | Technology | Purpose | Bonus Points |
|-----------|------------|---------|--------------|
| **Agent Framework** | LangGraph + Claude/OpenAI | Conversational assessment | Core |
| **Orchestration** | Akka (Pykka) | Actor-based state management | +10 pts |
| **Event Streaming** | Redpanda | Audit logging, compliance trail | +10 pts |
| **Authentication** | Auth0 | Secure RBAC (assessor/client/admin) | Judge: Fred Patton |
| **Observability** | Comet ML | Prompt tracking, decision logging | Judge: Claire Longo |
| **Backend** | FastAPI | RESTful API | Core |
| **Database** | PostgreSQL | Assessment data, control responses | Core |

**Target Judging Score:** 110-120 / 100 (with bonus points)

---

## Features

### Core Assessment Flow

1. **Authenticate via Auth0** - Secure login with role-based access
2. **Select Domain** - Start with Access Control (22 controls)
3. **Interactive Interview** - Agent asks contextual questions per control
4. **Real-time Scoring** - Traffic light classification (🟢 Compliant / 🟡 Partial / 🔴 Non-compliant)
5. **Gap Report** - Prioritized remediation plan with cost/time estimates

### Sample Conversation

```
Agent: Let's start with Access Control. First question:
       Do you have documented policies that limit system access
       to authorized users? (AC.L2-3.1.1)

User:  Yes, we have an access control policy.

Agent: Great. Can you briefly describe how access requests
       are approved and documented?

User:  Manager approval via email, then IT creates the account.

Agent: I'm marking this as PARTIAL. While you have a policy,
       email-based approvals lack audit trails. For full compliance,
       consider a ticketing system that logs approvals.

       Moving to the next control...
```

### Observability & Compliance

All assessment events streamed to **Redpanda** for audit trail:
- `assessment.started` - New assessment initiated
- `control.evaluated` - Control scored with classification
- `gap.identified` - Non-compliance detected
- `report.generated` - Final report created

All prompts and decisions logged to **Comet ML** for:
- Prompt performance tracking
- Assessment accuracy analysis
- Continuous improvement

---

## Quick Start

### Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose**
- **API Keys:**
  - Auth0 credentials
  - Comet ML API key
  - OpenAI or Anthropic API key

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/cmmc-scout.git
cd cmmc-scout

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Start infrastructure services
docker compose up -d

# 6. Initialize database
python scripts/init_db.py

# 7. Run the application
uvicorn src.main:app --reload
```

### Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Run tests
pytest --cov=src --cov-report=term-missing

# View Redpanda Console
open http://localhost:8080

# View API docs
open http://localhost:8000/docs
```

---

## Usage

### Starting an Assessment

```bash
# Create new assessment
curl -X POST http://localhost:8000/api/assessments/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"domain": "Access Control"}'

# Submit response to control
curl -X POST http://localhost:8000/api/assessments/{id}/respond \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"response": "Yes, we have documented access control policies..."}'

# Get assessment status
curl http://localhost:8000/api/assessments/{id}/status \
  -H "Authorization: Bearer $TOKEN"

# Generate gap report
curl http://localhost:8000/api/assessments/{id}/report \
  -H "Authorization: Bearer $TOKEN"
```

---

## CMMC Coverage

The agent assesses controls across all 14 NIST SP 800-171 domains:

1. **Access Control (AC)** - 22 controls
2. **Awareness and Training (AT)** - 3 controls
3. **Audit and Accountability (AU)** - 9 controls
4. **Configuration Management (CM)** - 9 controls
5. **Identification and Authentication (IA)** - 11 controls
6. **Incident Response (IR)** - 3 controls
7. **Maintenance (MA)** - 6 controls
8. **Media Protection (MP)** - 9 controls
9. **Personnel Security (PS)** - 2 controls
10. **Physical Protection (PE)** - 6 controls
11. **Risk Assessment (RA)** - 3 controls
12. **Security Assessment (CA)** - 4 controls
13. **System and Communications Protection (SC)** - 16 controls
14. **System and Information Integrity (SI)** - 7 controls

**Total: 110 controls**

---

## Development

### Project Structure

```
cmmc-scout/
├── src/
│   ├── main.py                 # FastAPI application
│   ├── auth/                   # Auth0 integration
│   ├── agents/                 # LangGraph assessment agent
│   ├── actors/                 # Akka actor system
│   ├── events/                 # Redpanda event streaming
│   ├── models/                 # Database models
│   ├── services/               # Business logic
│   └── data/
│       └── controls.json       # NIST 800-171 control data
├── tests/                      # Test suite
├── scripts/                    # Utility scripts
├── docker-compose.yml          # Infrastructure services
├── requirements.txt            # Python dependencies
├── claude.md                   # Project-specific development rules
└── DEVELOPMENT_PLAN.md         # Numbered subtask breakdown
```

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_scoring_service.py -v

# Run with debugging
pytest -s -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

### Monitoring Events

```bash
# Run event consumer (see events in real-time)
python scripts/consume_events.py

# View in Redpanda Console
open http://localhost:8080
```

---

## Security

### Authentication & Authorization

- **Auth0 OAuth 2.0** flow for user authentication
- **Role-Based Access Control (RBAC):**
  - `assessor` - Can conduct assessments
  - `client` - Can view own assessments
  - `admin` - Full system access
- **Token Security:**
  - Tokens never passed to LLM
  - Backend-only validation
  - Session timeout on inactivity

### Prompt Injection Protection

- User inputs sanitized before LLM processing
- System prompts isolated from user content
- Input validation on all endpoints

### Audit Trail

All assessment events logged to Redpanda with:
- Timestamp
- User ID
- Assessment ID
- Action type
- Complete context

---

## Vendor Integrations

### Akka (Pykka) - Actor System

**Use Case:** Stateful workflow orchestration

```
Assessment Actor System:
├── SessionActor - Manages user session state
├── DomainActor - Handles each CMMC domain
│   ├── ControlActor - Individual control assessment
│   └── EvidenceActor - Document collection (future)
├── ScoringActor - Calculates compliance scores
└── ReportActor - Generates remediation plan
```

**Benefits:**
- Fault tolerance if agent crashes mid-assessment
- Natural fit for long-running conversations
- Session state recovery
- Easy multi-agent validation later

### Redpanda - Event Streaming

**Use Case:** Compliance audit trail and analytics

**Event Topics:**
- `assessment.started`
- `control.evaluated`
- `evidence.submitted`
- `gap.identified`
- `report.generated`

**Benefits:**
- Required audit trail for compliance work
- Real-time dashboards for consultants
- Replay capability for debugging
- Analytics on assessment patterns

### Auth0 - Authentication

**Use Case:** Enterprise-grade security

**Implementation:**
- OAuth 2.0 authentication flow
- MFA support for sensitive data
- RBAC with fine-grained permissions
- Secure token handling

### Comet ML - Observability

**Use Case:** ML/AI monitoring and improvement

**Tracking:**
- Prompt versions and performance
- Agent decision paths per control
- User satisfaction metrics
- Assessment completion times
- Classification accuracy

**Benefits:**
- A/B test different prompts
- Identify struggling controls
- Build fine-tuning datasets
- Continuous improvement loop

---

## Roadmap

### MVP (Hackathon Demo) ✅
- [x] Auth0 authentication
- [x] Access Control domain assessment (10+ controls)
- [x] Real-time scoring (Red/Yellow/Green)
- [x] Gap report generation
- [x] Redpanda event streaming
- [x] Akka actor orchestration
- [x] Comet ML tracking

### Post-Hackathon
- [ ] All 14 domains (110 controls)
- [ ] Evidence upload (PDFs, screenshots)
- [ ] POA&M generation in C3PAO format
- [ ] Multi-user collaboration
- [ ] Progress save/resume
- [ ] Export to PDF/Word
- [ ] Mobile app for on-site assessments

### Future
- [ ] Azure/M365 integration for automated evidence
- [ ] Fine-tuned LLM on validated assessment data
- [ ] Integration with GRC tools (Archer, ServiceNow)
- [ ] Continuous compliance monitoring
- [ ] Automated remediation suggestions

---

## Contributing

This is a hackathon project. For post-hackathon development:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the development guidelines in [claude.md](claude.md)
4. Run tests and ensure >70% coverage
5. Commit with semantic messages (`feat:`, `fix:`, etc.)
6. Push to your branch
7. Open a Pull Request

---

## License

MIT License - see [LICENSE](LICENSE) file for details

---

## Acknowledgments

**Hackathon:** AI By the Bay - Hack the Bay (November 18-19, 2025)

**Vendor Partners:**
- **Akka** - Hugh McKee (mentor)
- **Redpanda** - Chandler Mayo (mentor)
- **Auth0** - Fred Patton (judge)
- **Comet ML** - Claire Longo (judge)

**References:**
- [NIST SP 800-171 Rev 2](https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final)
- [CMMC Model](https://dodcio.defense.gov/CMMC/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

## Contact

**Project Lead:** Mike Morris
**Email:** mike@mikemorris.net
**GitHub:** [@mmorris35](https://github.com/mmorris35)

**Use Case Inquiries:**
If you're a defense contractor or CMMC consultant interested in this tool, please reach out!

---

<div align="center">

**Built with** [Claude Code](https://claude.com/claude-code)

*Helping defense contractors achieve CMMC compliance faster and cheaper*

</div>
