# CMMC Compliance Assessment Agent - Project Brief

## Project Overview

**Project Name:** CMMC Scout  
**Hackathon:** AI By the Bay - Hack the Bay (Nov 18-19, 2025)  
**Time Budget:** ~4 hours development  
**Team Size:** Solo or small team  

### Elevator Pitch

An AI agent that conducts interactive CMMC Level 2 compliance assessments for defense contractors. The agent interviews users about their security practices, maps responses to the 110 controls in NIST SP 800-171, identifies gaps, and generates a prioritized remediation plan with estimated costs and timelines.

---

## Problem Statement

Defense contractors pursuing CMMC Level 2 certification face a complex, expensive assessment process. Most don't know where they stand until they pay $50K+ for a formal C3PAO assessment. They need a way to:

1. Understand their current compliance posture
2. Identify specific gaps before formal assessment
3. Prioritize remediation efforts by cost and impact
4. Track progress toward certification

### Target Users

- Small to mid-size defense contractors (DIB sector)
- MSPs serving defense contractors
- CMMC consultants conducting pre-assessments

### Business Value

- **B2B SaaS potential:** $500-2000/month per contractor
- **Clear adoption path:** Consultants can white-label for their clients
- **Reduces risk:** Contractors avoid failed assessments ($15-30K wasted)

---

## Technical Architecture

### Core Components

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

| Component | Technology | Purpose |
|-----------|------------|---------|
| Agent Framework | LangGraph or LangChain | Conversation management, tool use |
| Orchestration | **Akka** (+10 pts) | State management, workflow actors |
| Event Streaming | **Redpanda** (+10 pts) | Audit logging, assessment events |
| Authentication | **Auth0** (judge: Fred Patton) | Secure access, RBAC |
| Observability | **Comet** (judge: Claire Longo) | Prompt tracking, decision logging |
| LLM | Claude API or OpenAI | Assessment conversations |
| Backend | Python (FastAPI) or Node.js | API layer |
| Data Store | PostgreSQL or SQLite | Control mappings, user responses |

---

## Vendor Integrations (Bonus Points Strategy)

### Akka Integration (+10 points)

**Use Case:** Actor-based workflow orchestration

```
Assessment Actor System:
├── SessionActor (manages user session state)
├── DomainActor (handles each of 14 CMMC domains)
│   ├── ControlActor (individual control assessment)
│   └── EvidenceActor (document/screenshot collection)
├── ScoringActor (calculates compliance scores)
└── ReportActor (generates remediation plan)
```

**Why Akka:** 
- Natural fit for stateful, long-running assessment conversations
- Fault tolerance if agent crashes mid-assessment
- Easy to add multi-agent validation later

**Mentor:** Hugh McKee at Akka booth

### Redpanda Integration (+10 points)

**Use Case:** Event streaming for audit and analytics

**Event Topics:**
- `assessment.started` - New assessment initiated
- `control.evaluated` - Individual control scored
- `evidence.submitted` - User uploaded documentation
- `gap.identified` - Non-compliance detected
- `report.generated` - Final report created

**Why Redpanda:**
- Audit trail required for compliance work
- Real-time dashboards for consultants managing multiple clients
- Replay capability for debugging agent decisions

**Mentor:** Chandler Mayo at Redpanda booth

### Auth0 Integration (Judge: Fred Patton)

**Use Case:** Authentication and authorization

**Implementation:**
- OAuth 2.0 flow for user authentication
- RBAC: `assessor`, `client`, `admin` roles
- Secure token handling (no leakage to LLM)
- MFA for sensitive assessment data access

**Security Considerations:**
- Agent never sees raw tokens
- All API calls go through authenticated backend
- Session timeout for inactive assessments

### Comet Integration (Judge: Claire Longo)

**Use Case:** ML observability and prompt engineering

**What to Track:**
- Prompt versions and their performance
- Agent decision paths per control
- User satisfaction with explanations
- Time-to-completion per domain
- Accuracy of gap identification (validation set)

**Benefits:**
- A/B test different assessment prompts
- Identify controls where agent struggles
- Build dataset for fine-tuning

---

## CMMC Domain Coverage

The agent assesses all 14 domains in NIST SP 800-171 / CMMC Level 2:

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

## MVP Feature Set (4-Hour Build)

### Must Have (Core Loop)

1. **User Authentication**
   - Auth0 login flow
   - Session management

2. **Assessment Interview**
   - Select domain to assess
   - Agent asks contextual questions about each control
   - Accepts yes/no/partial/unknown responses
   - Asks for evidence descriptions

3. **Real-Time Scoring**
   - Traffic light status per control (Red/Yellow/Green)
   - Domain-level compliance percentage
   - Overall assessment score

4. **Gap Report Generation**
   - List of non-compliant controls
   - Plain-English explanation of each gap
   - Suggested remediation steps
   - Rough cost/time estimates

5. **Event Streaming**
   - All assessment events to Redpanda
   - Basic audit log viewer

### Nice to Have (If Time Permits)

- Evidence upload (screenshots, policy docs)
- POA&M (Plan of Action & Milestones) generation
- Export to PDF/Word
- Multi-user assessment collaboration
- Progress save/resume

### Out of Scope (Future)

- Full 110-control deep assessment
- Integration with GRC tools
- Automated evidence collection from Azure/M365
- C3PAO report formatting

---

## Agent Conversation Design

### Sample Interaction Flow

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

### Prompt Engineering Considerations

- Use few-shot examples for consistent scoring
- Include control text and assessment objectives in context
- Maintain conversation history per domain
- Clear escalation when user is uncertain

---

## Judging Criteria Alignment

| Criterion | Points | How We Address It |
|-----------|--------|-------------------|
| Business Value & User Impact | 20 | Real B2B problem, clear adoption path, $50K+ assessment cost savings |
| Production Readiness | 20 | Akka state management, error handling, session recovery |
| Security & Safety | 20 | Auth0 RBAC, no token leakage, input validation, prompt injection guards |
| Observability & Operability | 20 | Comet tracking, Redpanda audit logs, health metrics |
| Knowledge & Reasoning | 15 | NIST 800-171 control mappings, explainable gap analysis |
| Bonus: Multi-Agent | +5 | Validator agent reviews assessments (stretch goal) |
| Bonus: Redpanda | +10 | Event streaming for all assessment events |
| Bonus: Akka | +10 | Actor-based workflow orchestration |

**Maximum Possible Score: 120 points**

---

## Development Plan Outline

### Phase 1: Foundation (1 hour)

- [ ] Project scaffolding (FastAPI or Node)
- [ ] Auth0 integration and login flow
- [ ] Basic database schema (users, assessments, responses)
- [ ] Redpanda topic setup
- [ ] Comet project initialization

### Phase 2: Agent Core (1.5 hours)

- [ ] LLM integration (Claude or OpenAI)
- [ ] Control data loading (start with 1 domain, ~10 controls)
- [ ] Conversation state management with Akka actors
- [ ] Scoring logic (Red/Yellow/Green)
- [ ] Event emission to Redpanda

### Phase 3: Reporting (1 hour)

- [ ] Gap identification aggregation
- [ ] Remediation suggestion generation
- [ ] Simple report output (Markdown or JSON)
- [ ] Basic UI or CLI for demo

### Phase 4: Polish (30 min)

- [ ] Demo script preparation
- [ ] 3-minute video recording
- [ ] README and repo cleanup
- [ ] Devpost submission

---

## Demo Script (3 minutes)

**0:00-0:30** - Problem statement and market opportunity  
**0:30-1:00** - Live login via Auth0, start new assessment  
**1:00-2:00** - Walk through 3-4 control assessments, show scoring  
**2:00-2:30** - Generate gap report, show remediation suggestions  
**2:30-3:00** - Show Redpanda event stream and Comet dashboard  

---

## Repository Structure

```
cmmc-scout/
├── README.md
├── requirements.txt / package.json
├── docker-compose.yml          # Redpanda, DB
├── src/
│   ├── main.py                 # FastAPI app
│   ├── auth/                   # Auth0 integration
│   ├── agents/                 # LLM agent code
│   ├── actors/                 # Akka actor definitions
│   ├── events/                 # Redpanda producers
│   ├── models/                 # Database models
│   └── data/
│       └── controls.json       # NIST 800-171 control data
├── tests/
└── demo/
    └── script.md
```

---

## Resources Needed

### APIs and Services

- **LLM API Key:** Claude API or OpenAI API
- **Auth0:** Free tier sufficient for demo
- **Comet:** Free tier for experiment tracking
- **Redpanda:** Local Docker instance or Redpanda Cloud free tier

### Reference Data

- NIST SP 800-171 Rev 2 control catalog
- CMMC Level 2 assessment guide
- Sample POA&M templates

### Mentor Support

- **Hugh McKee (Akka)** - Actor system design
- **Chandler Mayo (Redpanda)** - Event streaming setup
- **Fred Patton (Auth0)** - Auth flow best practices
- **Claire Longo (Comet)** - Observability instrumentation

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Akka learning curve | Start with simple actor, get mentor help early |
| Too many controls | Demo with 1 domain (Access Control only) |
| LLM rate limits | Cache responses, use smaller model for dev |
| Time crunch | Prioritize core loop over UI polish |
| Redpanda setup issues | Have local fallback (file-based logging) |

---

## Success Criteria

1. **Functional demo** showing complete assessment flow for at least one domain
2. **All four vendor integrations** working and visible in demo
3. **Production-ready characteristics** clearly demonstrated:
   - Secure authentication
   - Audit logging
   - Error handling
   - Observability
4. **Clear business value** articulated in presentation
5. **3-minute video** submitted by 11:00 AM Wednesday

---

## Post-Hackathon Potential

This project has legs beyond the hackathon:

- **Immediate:** Use for Quick SCIF LLC client pre-assessments
- **Short-term:** Package as SaaS for CMMC consultants
- **Medium-term:** Expand to full 110 controls with evidence collection
- **Long-term:** Integrate with Azure/M365 for automated evidence gathering

---

## Notes for Claude Code

When generating the dev plan from this brief:

1. **Prioritize the vendor integrations** - they're worth 20 bonus points
2. **Start with Access Control domain only** - 22 controls is enough for demo
3. **Use Python/FastAPI** - faster to prototype than Node for this use case
4. **Keep UI minimal** - CLI or simple web form is fine
5. **Hardcode control data** - don't waste time on data ingestion
6. **Test the Akka/Redpanda integration early** - highest risk items

The goal is a working demo that hits all judging criteria, not a production system.
