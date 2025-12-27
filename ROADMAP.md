# Roadmap: From Today’s Flow to a Full Conversational System

This roadmap is optimized for your current stack (SIP bot + VAD/ASR + intent classifier with `"default"` fallback) while keeping a clean migration path to a full conversational platform (e.g., Rasa) later.

---

### Goals

- **Ship the exact flow you described** (max 2 retries, “any other questions” loop, human fallback).
- **Keep voice/SIP orchestration in one place** (timing, barge-in, VAD windows, hangup/transfer).
- **Make the “brain” replaceable later** (swap rule/LLM intent policy → Rasa/agent service with minimal rewrites).

---

### Core product decisions (lock these first)

- **Definition: “bot knows the answer”**
  - Recommended: `intent != "default"` **and** `confidence >= INTENT_MIN_CONFIDENCE`.
  - Start with a conservative threshold (e.g., `0.5`) and tune with production logs.
- **Definition: “human support”**
  - Choose one:
    - **SIP transfer (blind transfer/REFER)** to a PBX queue/extension (recommended for “transfer call” UX).
    - **Message + hangup** (fastest to ship; still valid if PBX transfer isn’t available).
  - If SIP transfer: decide `SUPPORT_SIP_URI` (e.g., `sip:2000@pbx.example.local`) and failure fallback behavior.
- **Audio assets**
  - Record (or TTS-generate) short prompts:
    - “Did you have any other questions?”
    - “Do you want to ask again, or fallback to human support?”
    - “Goodbye”

---

### Phase 1 — Implement your flow as a call-level state machine (ship fast)

**Outcome:** Your flow works end-to-end with strict limits.

**Add a per-call conversation state** (serialize-friendly dict is ideal):
- `question_attempts`: int (max 2 for “ask again” on unknown)
- `followup_rounds`: int (max 2 for “any other questions” after known answer)
- `pending_prompt`: enum/string (`NONE`, `ANY_OTHER_Q`, `REPEAT_OR_SUPPORT`)
- `last_intent`, `last_confidence`, `last_transcript`
- `handoff_requested`: bool

**Turn execution loop (high-level):**
- **User asks question** (transcript from ASR).
- **Classify** → `(intent, confidence)`.
- If **known**:
  - Play the intent’s answer audio.
  - Play “any other questions?”
  - If user says **yes** and `followup_rounds < 2`: re-arm listening and continue.
  - Else: play “goodbye” and end call.
- If **unknown**:
  - Play “repeat or support?”
  - If user chooses **repeat** and `question_attempts < 2`: re-arm listening and continue.
  - If user chooses **support**: trigger handoff.
  - If limits exceeded: default to support (or goodbye) depending on policy.

**Implementation notes (important for voice):**
- Make prompts **short**, and ensure **prompt playback and ASR capture don’t overlap** (avoid “listening while speaking” unless you implement barge-in).
- When you “re-arm listening”, reset only what’s necessary:
  - Clear ASR chunk buffer for the next user utterance.
  - Reset VAD chunking/hangup timing for the next question window.
- Keep a hard timeout for “no response” after a question prompt (e.g., 8–12 seconds) to avoid stuck calls.

**Acceptance criteria:**
- Known-answer path loops up to **2** follow-ups, then ends.
- Unknown-answer path allows **2** re-asks, then escalates/handoffs.
- If the user hangs up early, cleanup is safe.

---

### Phase 2 — Human support handoff (make escalation real)

**Outcome:** Unknown cases can reliably reach a human (or cleanly fall back).

Choose one of these implementations:

- **Option A (recommended): SIP blind transfer**
  - Trigger SIP transfer to `SUPPORT_SIP_URI`.
  - If transfer fails: play “Sorry, I couldn’t transfer you. Goodbye.” then hang up.

- **Option B: Message + hangup**
  - Play a message like “Please contact human support at …” then hang up.

**Acceptance criteria:**
- Handoff can be triggered explicitly by user choice.
- Transfer failures are logged and do not crash the call.

---

### Phase 3 — Production hardening (stability + quality)

**Outcome:** Fewer misfires, better timing, better analytics.

- **Confidence policy**
  - Add `INTENT_MIN_CONFIDENCE` and tune it.
  - Consider additional guardrails:
    - If transcript is very short/noisy → treat as unknown.
    - If intent is high-risk → require higher confidence.
- **Choice parsing**
  - Add lightweight parsing for “yes/no”, “repeat/support” (keywords + normalization).
  - (Optional) add dedicated intents for `affirm`, `deny`, `request_human`.
- **Barge-in (optional)**
  - If you want callers to interrupt prompts, add controlled barge-in:
    - Stop playback when VAD detects speech above threshold.
    - Only if your PBX/caller devices behave well.
- **Observability**
  - Log per call:
    - transcript, intent/confidence, unknown rate, retries used, handoff count, transfer success/failure, total call duration.

---

### Phase 4 — Future-proofing: introduce a “Brain” interface (key migration step)

**Outcome:** You can swap the dialogue engine without rewriting SIP/audio orchestration.

Create a single interface your SIP bot calls:

**Input (example schema):**
- `session_id`
- `turn_index`
- `user_text`
- `state` (the conversation state dict)
- `capabilities` (e.g., supports_transfer, supports_tts, etc.)

**Output (example schema):**
- `actions`: ordered list (e.g., `PLAY_AUDIO`, `ASK`, `HANDOFF`, `END_CALL`)
- `audio_asset` or `response_text`
- `updated_state`
- `handoff` (optional): `{ "type": "sip_transfer", "target": "sip:..." }`

**Rule:** The SIP bot remains responsible for:
- when to listen, when to speak
- playing audio, handling timing
- hangup/transfer mechanics

The “brain” decides:
- what to say next
- whether it’s known/unknown
- how to handle retries and handoff policy

---

### Phase 5 — Add a full conversational engine (Rasa or alternative) behind the interface

**Outcome:** Multi-turn dialogue grows without turning into complex, brittle code.

- Run the engine as a **separate service/container** (important if the engine has Python/runtime constraints).
- Start by replicating your existing behavior:
  - intents: FAQ intents + `affirm/deny` + `repeat/support`
  - rules: implement your 2× retry loops and escalation
- Only move complexity into the engine once it’s justified:
  - slots/entities, forms, personalization, memory, richer fallback strategies.

---

### When to switch to “full conversational”

Switch when you have one or more of:
- Many multi-turn paths (slot filling, branching workflows, troubleshooting trees)
- Strong need for entity extraction and persistent context
- Non-engineers maintaining dialogue logic/training data
- Rapid iteration requirements that are painful in code

---

### Suggested timeline (typical)

- **Phase 1**: 2–5 days
- **Phase 2**: 1–3 days
- **Phase 3**: 3–10 days (ongoing tuning)
- **Phase 4**: 2–5 days
- **Phase 5**: 1–3+ weeks (depends heavily on training data and iteration)



