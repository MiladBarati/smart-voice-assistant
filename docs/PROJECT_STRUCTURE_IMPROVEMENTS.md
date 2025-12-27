# Project Structure & Refactoring Overview

This document merges the repository structure improvement plan with the `register_bot.py` refactoring summary. Use it as the single source of truth for the ongoing structural workstream.

## Snapshot

- Test suite already lives in `tests/`; audio, recordings, and infrastructure assets are scoped cleanly.
- Utility and demo scripts still mix with application modules at the repository root.
- ✅ `pyproject.toml` is the authoritative dependency manifest; `requirements.txt` has been removed.
- Modularization work split the 1081-line `register_bot.py` into focused modules under `src/pjsua_bot/`, but follow-up cleanup is pending.

## ✅ Completed Work

### Quick Wins Implemented

- `.gitignore` excludes coverage artefacts (`.coverage`, `artifacts/coverage.xml`, `artifacts/htmlcov/`) and cache directories (`.pytest_cache/`).
- Broader Python build artefacts are ignored to prevent noisy commits.

### Modularization Delivered

- The monolithic `register_bot.py` (1030 lines) has been decomposed into focused modules that follow the Single Responsibility Principle.
- New package structure:

```
src/pjsua_bot/
├── __init__.py          # Package exports (updated)
├── utils.py             # Utility helpers
├── account.py           # SIP account lifecycle
├── calls/               # Call media handling
│   ├── any_call.py
│   ├── out_call.py
│   └── ...
├── config.py            # Bot configuration management
├── endpoint.py          # Endpoint setup and configuration
├── account_setup.py     # Account configuration
├── services.py          # ASR and Intent service initialization
├── registration.py      # Registration and call handling
├── shutdown.py          # Shutdown orchestration
├── cleanup.py           # Resource cleanup functions
└── register_bot.py      # CLI entry point and orchestration (~300 lines)
```

## 🎯 Quick Wins Ready to Implement

1. **Create directory scaffolding**  
   - `src/pjsua_bot/` for primary application code (already hosting the refactored modules)  
   - `scripts/` for utilities, demos, and operational tooling  
   - *Impact*: High | *Effort*: 2 minutes

2. **Move utility scripts into `scripts/`**  
   - Candidates: `run_tests.py`, `demo_tests.py`, `test_connectivity.py`, `test_elasticsearch.py`  
   - *Impact*: Medium | *Effort*: 3 minutes

3. **Organize remaining application code under `src/`**  
   - Move `register_bot.py`, `elasticsearch_client.py`, and related helpers already refactored  
   - Add missing `__init__.py` files where required to cement package semantics  
   - *Impact*: High | *Effort*: 10 minutes

4. **Clean up dependency files**  
   - ✅ **COMPLETED**: Removed redundant `requirements.txt` (verified `pyproject.toml` is authoritative)
   - *Impact*: Low | *Effort*: 1 minute

5. **Polish documentation layout**  
   - Keep all guides inside `docs/` and update references to point at the modularized modules  
   - *Impact*: Medium | *Effort*: 5 minutes

## Current Issues

1. **Root Directory Clutter**  
   - Multiple Python entry points (`register_bot.py`, `mwe_register.py`, `main.py`) and demos live beside configuration files.
   - Scripts and application modules are intermingled, complicating onboarding.

2. **Incomplete Package Structure**  
   - `src/pjsua_bot/` exists, but some helpers still sit at the root and lack `__init__.py` coverage.
   - Implicit namespace packages risk accidental module shadowing.

3. **Configuration Drift**  
   - ✅ Legacy dependency lists (`requirements.txt`) removed; `pyproject.toml` is now the single source of truth.
   - `.env.example` is available, yet documentation should mirror actual configuration options.

4. **Documentation Sync**  
   - Several guides reference pre-refactor paths; they need consolidation around the new layout.

## Recommended Repository Layout

```
pjsua-installation/
├── src/
│   └── pjsua_bot/
│       ├── __init__.py
│       ├── register_bot.py
│       ├── elasticsearch_client.py
│       ├── account.py
│       ├── calls.py
│       └── utils.py
├── scripts/
│   ├── run_tests.py
│   ├── demo_tests.py
│   ├── test_connectivity.py
│   └── test_elasticsearch.py
├── examples/
│   └── asr_usage_example.py
├── tests/
│   └── [...]
├── assets/
│   └── audio/
├── recordings/
│   └── [date directories]
├── infrastructure/
│   ├── freepbx/
│   └── nginx/
├── docs/
│   └── [...]
├── pyproject.toml
├── pytest.ini
├── README.md
└── LICENSE
```

## Module Breakdown

### Core Modules

#### `utils.py`
- Shared helpers such as `generate_unique_id()`, `parse_sip_user()`, `setup_logging()`, `get_wav_duration()`, `ensure_recording_directory()`, `pump_events()`, and `wait_until()`.

#### `account.py`
- The `Account` class manages SIP registration, handling `onRegState()` updates and `onIncomingCall()` events.

#### `calls/` (package)
- Implements `OutCall` and `AnyCall` to coordinate playback, recording, and media state transitions.
- Contains helpers like `check_playback_status()`, `should_hangup()`, and `_cleanup_recording()` for lifecycle management.

### Bot Orchestration Modules (from `register_bot.py` refactoring)

#### `config.py`
- `BotConfig` dataclass containing all bot configuration options
- `from_args()` method to create configuration from command-line arguments

#### `endpoint.py`
- `create_endpoint_config()`: Creates and configures PJSUA2 endpoint settings
- `configure_codecs()`: Sets codec priorities (wideband preferred)
- `create_transport()`: Creates SIP transport (UDP/TCP/TLS)

#### `account_setup.py`
- `create_account_config()`: Creates PJSUA2 account configuration
- `configure_account()`: Configures Account instance with bot settings

#### `services.py`
- `initialize_asr_service()`: Initializes ASR service if enabled
- `initialize_intent_classifier()`: Initializes intent classifier (rule-based or Ollama)

#### `registration.py`
- `wait_for_registration()`: Waits for SIP account registration
- `handle_outbound_call()`: Handles outbound call if destination specified
- `run_main_loop()`: Main event loop for receiving incoming calls

#### `shutdown.py`
- `stop_asr_threads()`: Stops all ASR worker threads
- `hangup_all_calls()`: Hangs up all active calls
- `unregister_account()`: Unregisters SIP account
- `destroy_transports()`: Destroys all SIP transports
- `shutdown_gracefully()`: Orchestrates complete graceful shutdown

#### `cleanup.py`
- `cleanup_resources()`: Cleans up ASR models, intent classifiers, and Elasticsearch connections
- Handles CUDA cache clearing for GPU resources

#### `register_bot.py`
- Reduced to ~300 lines (from 1030 lines)
- `parse_arguments()`: Command-line argument parsing
- `setup_signal_handlers()`: Signal handling for graceful shutdown
- `main()`: Main entry point that orchestrates all components

## Implementation Phases & Options

### Phase 1 – Quick Wins (safe to execute immediately)
1. Create `scripts/` and move utility scripts.
2. Confirm `.gitignore` changes are committed (already complete).
3. Remove stale build artefacts from the root.

### Phase 2 – Package Structure
1. Consolidate all application modules under `src/pjsua_bot/`.
2. Add `__init__.py` files and update import paths.
3. Run `pytest` to validate import changes.

### Phase 3 – Polish
1. Refresh documentation to reflect the new layout.
2. Review remaining root-level files and archive anything obsolete.
3. Add packaging metadata (`setup.cfg` or `setup.py`) only if distribution is required.

**Execution choices**
- *Option A: Conservative*: execute Phase 1, validate, then iterate.
- *Option B: Full Restructure*: deliver Phases 1–3 in one branch for a production-ready layout.
- *Option C: Hybrid*: Phase 1 plus key steps from Phase 2 to unblock imports while keeping examples at the root.

## Import & Compatibility Notes

```python
# Before (monolithic module)
from src.pjsua_bot import register_bot

# After (package exports retained)
from src.pjsua_bot import Account, OutCall, AnyCall, main

# Alternative targeted imports
from src.pjsua_bot.account import Account
from src.pjsua_bot.calls import OutCall, AnyCall
from src.pjsua_bot.utils import setup_logging, pump_events
from src.pjsua_bot.register_bot import main
```

`src/pjsua_bot/__init__.py` now re-exports the primary classes to maintain backward compatibility with existing import statements.

## Benefits

- **Immediate**: Discoverability improves, clutter drops, and imports become explicit.
- **Long-term**: Ready-to-package layout, better IDE support, and clearer contributor experience.
- **Operational**: Consistent script locations simplify automation and CI integration.

## Migration Checklist

1. Create the new directory structure.
2. Move files and update imports.
3. ✅ Remove `requirements.txt` after verifying parity with `pyproject.toml` - **COMPLETED**
4. Run `pytest tests/` or `python scripts/run_tests.py`.
5. Update documentation references (`README.md`, onboarding guides).

## Testing & Risk

- **Risk level**: Low, provided imports are updated atomically.
- **Breaking changes**: None expected for CLI usage (`python register_bot.py ...`) once entry points are adjusted.
- **Testing**: Execute existing automated tests plus smoke-test Elasticsearch integration.
- **Rollback**: Straightforward via git history if issues arise.

### Testing Focus Areas

1. Registration flow (`Account` module).
2. Incoming and outgoing call handling (`AnyCall`, `OutCall`).
3. Media playback and recording lifecycle, including FFmpeg conversions.
4. Elasticsearch logging and metadata persistence.

## Documentation Impact

- `README.md` now mirrors the modular repository layout and references the `src/pjsua_bot/` package.
- Import examples have been updated to highlight package-level, module-specific, and `main()` entry points.
- Duplicated project structure snippets were removed to avoid confusion.
- Version markers and the contributing checklist acknowledge the modularization milestone.

## Next Steps

1. Run the full test suite to confirm behaviour after relocations.
2. Update CI/CD scripts to reference `scripts/` and the new package layout.
3. Add unit tests for the newly separated modules.
4. Continue polishing documentation to keep pace with structural changes.


