# Mac Local Setup Instructions

## Context

We've been developing remotely on an Ubuntu server, but need to run locally on your Mac for:
- ✅ Seeing colored terminal output from the demo CLI
- ✅ Recording screen for demo video
- ✅ Running Docker Desktop for Redpanda (optional)
- ✅ Better development experience with real TTY

## Current Project Status

**What's Working (182 tests passing, 78% coverage):**
- ✅ Database models and CMMC control data (110 controls across 14 domains)
- ✅ Scoring logic and gap identification
- ✅ Report generation (Markdown + JSON)
- ✅ Demo CLI with predefined responses (no LLM needed)
- ✅ Sample report generator

**What's in the Repo:**
- Complete codebase committed to `main` branch
- [DEMO.md](DEMO.md) - 3-minute presentation script
- [README.md](README.md) - Full documentation
- `scripts/demo_cli.py` - Interactive colored demo
- `scripts/generate_sample_report.py` - Sample report generator

## Setup Steps on Mac

### 1. Clone Repository Locally

```bash
# Navigate to your projects folder
cd ~/projects  # or wherever you keep projects

# Clone the repo
git clone https://github.com/mmorris35/cmmc-scout.git
cd cmmc-scout
```

### 2. Set Up Python Environment

```bash
# Create virtual environment (Python 3.12+ recommended)
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env file - add your Anthropic API key
```

Edit `.env` and uncomment/update this line:
```bash
ANTHROPIC_API_KEY=your-actual-key-from-anthropic-console
```

**Note:** Your Anthropic key only works with `claude-3-haiku-20240307` model, not the newer Sonnet models. This is fine for the demo.

### 4. Run the Demo

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Run the interactive demo CLI (shows colored output!)
python scripts/demo_cli.py

# Generate sample report
python scripts/generate_sample_report.py
```

**What You'll See:**
- Colored terminal output (green for compliant, yellow for partial, red for non-compliant)
- 4 control assessments with predefined responses
- Real-time "AI analysis" (actually using mock data for reliability)
- Final score: 62.5% (YELLOW)
- Generated `demo_report.md` file

### 5. Run Tests (Optional)

```bash
# Run full test suite
pytest --cov=src --cov-report=term-missing

# Expected: 182 tests passing, 78% coverage
```

### 6. Docker Services (Optional)

If you want to show Redpanda event streaming in the demo:

```bash
# Make sure Docker Desktop is installed and running on Mac

# Start services
docker compose up -d

# View Redpanda console
open http://localhost:8080
```

**Note:** The demo works fine WITHOUT Docker. Events will fall back to file logging.

## What the Demo Shows

When you run `python scripts/demo_cli.py`, you'll see:

1. **Welcome screen** with project title
2. **4 Control Assessments:**
   - AC.L2-3.1.1: ✓ COMPLIANT (good access control)
   - AC.L2-3.1.2: ✓ COMPLIANT (strong RBAC)
   - AC.L2-3.1.3: ⚠ PARTIAL (some separation gaps)
   - AC.L2-3.1.4: ✗ NON-COMPLIANT (no session timeout)
3. **Gap Report Generated:**
   - Overall score: 62.5%
   - Traffic light: YELLOW
   - 2 gaps identified (1 high priority, 1 medium)
   - Remediation recommendations
   - Saved to `demo_report.md`

## Recording Demo Video

Once you have it running on your Mac:

1. **Open Terminal** in fullscreen or large window
2. **Start screen recording** (Cmd+Shift+5 on Mac)
3. **Run the demo:** `python scripts/demo_cli.py`
4. **Press ENTER** at each prompt to advance
5. **Stop recording** when complete
6. **Add voiceover** or captions following [DEMO.md](DEMO.md) script

## Files to Review

Before recording, read these files:

- **[DEMO.md](DEMO.md)** - Complete 3-minute presentation script with timing
- **[README.md](README.md)** - Project overview and documentation
- **[sample_report.md](sample_report.md)** - Example of generated report (after running demo)

## Known Limitations

**What Doesn't Work Without Full Setup:**
- ❌ Real LLM-powered question generation (demo uses predefined questions)
- ❌ Comet ML tracking dashboard (needs COMET_API_KEY)
- ❌ Auth0 authentication flow (needs Auth0 credentials)
- ❌ Redpanda event streaming (needs Docker running)
- ❌ Full API server (needs PostgreSQL)

**But That's OK!** The demo CLI shows the complete workflow with:
- ✅ Realistic questions and responses
- ✅ Intelligent classification logic
- ✅ Professional gap reports
- ✅ All the visual polish needed for the video

## Phase 4 - Next Steps for Hackathon

According to `DEVELOPMENT_PLAN.md`, you're on:

**Subtask 4.2: Video Recording and Submission**
- [ ] Record 3-minute demo video following DEMO.md script
- [ ] Add voiceover or captions explaining each step
- [ ] Highlight all four vendor integrations visibly
- [ ] Upload video to YouTube (unlisted) or file
- [ ] Complete Devpost submission

## Quick Reference Commands

```bash
# Activate environment
source venv/bin/activate

# Run demo
python scripts/demo_cli.py

# Generate sample report
python scripts/generate_sample_report.py

# Run tests
pytest --cov=src

# Start Docker services (optional)
docker compose up -d

# View Redpanda console (if Docker running)
open http://localhost:8080
```

## Troubleshooting

**"ModuleNotFoundError":**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**"No such file demo.db":**
- This is normal - the demo creates it on first run
- If you get errors, try: `rm demo.db` and run again

**Anthropic API errors:**
- Make sure `.env` has your API key
- The key only works with Haiku model (already configured)

**Colored output not showing:**
- Make sure you're running directly in Terminal (not through an IDE)
- Some terminals don't support ANSI colors

## Project Structure

```
cmmc-scout/
├── DEMO.md                    # 3-minute presentation script
├── README.md                  # Project documentation
├── MAC_SETUP_INSTRUCTIONS.md  # This file!
├── DEVELOPMENT_PLAN.md        # Phase-by-phase plan
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── docker-compose.yml         # Infrastructure services
├── scripts/
│   ├── demo_cli.py           # Interactive demo ⭐
│   └── generate_sample_report.py
├── src/
│   ├── agents/               # LLM assessment agent
│   ├── actors/               # Akka (Pykka) actors
│   ├── api/                  # FastAPI routes
│   ├── auth/                 # Auth0 integration
│   ├── events/               # Redpanda event streaming
│   ├── models/               # Database models
│   ├── services/             # Business logic ⭐
│   │   ├── control_service.py
│   │   ├── scoring_service.py
│   │   ├── gap_service.py
│   │   └── report_service.py
│   └── data/
│       └── controls.json     # 110 NIST SP 800-171 controls
└── tests/                    # 182 passing tests

⭐ = Most important files for demo
```

## Success Criteria

You'll know it's working when:
- ✅ Demo CLI shows colored output
- ✅ 4 controls assessed with classifications
- ✅ `demo_report.md` file created
- ✅ No Python errors or crashes
- ✅ Output looks professional and polished

## Contact for Questions

If you run into issues, check:
1. This file (MAC_SETUP_INSTRUCTIONS.md)
2. [README.md](README.md) for general info
3. [DEMO.md](DEMO.md) for presentation script
4. GitHub Issues if something is broken

---

**Last Updated:** 2025-11-19
**Commit:** 4e4e3c8 (fix: Make demo CLI work without LLM API dependencies)
**Status:** Ready for Mac local setup and demo recording
