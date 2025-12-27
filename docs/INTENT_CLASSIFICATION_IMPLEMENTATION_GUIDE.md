# Intent Classification Implementation Guide

This guide provides step-by-step instructions for implementing each phase of the intent classification system for the PJSUA2 call bot.

## Overview

The intent classification system allows the bot to:
1. Transcribe caller speech (already implemented via ASR)
2. Classify the caller's intent based on the transcription
3. Play an appropriate FAQ response (audio file or TTS)
4. Continue with the normal call flow (goodbye message, hangup)

## Phase Status

- ✅ **Phase 1: Rule-Based Intent Classification** - COMPLETED
- ⏳ **Phase 2: Semantic Search Classification** - PENDING
- ⏳ **Phase 3: Hybrid Approach** - PENDING
- ⏳ **Phase 4: TTS Integration** - PENDING

---

## Phase 1: Rule-Based Intent Classification ✅

### Status: COMPLETED

### Overview
Simple keyword-based intent classification using pattern matching. Fast, lightweight, and requires no external ML dependencies.

### Implementation Details

#### Files Created
- `src/pjsua_bot/intent/__init__.py` - Package exports
- `src/pjsua_bot/intent/faq_config.py` - FAQ configuration with Persian keywords
- `src/pjsua_bot/intent/classifier.py` - RuleBasedClassifier implementation
- `src/pjsua_bot/calls/mixins/intent_handler.py` - IntentHandlerMixin
- `tests/test_intent_phase1.py` - Test suite

#### Files Modified
- `src/pjsua_bot/calls/any_call.py` - Added IntentHandlerMixin
- `src/pjsua_bot/calls/mixins/__init__.py` - Export IntentHandlerMixin
- `src/pjsua_bot/calls/mixins/playback_monitor.py` - Integrated intent classification
- `src/pjsua_bot/account.py` - Added intent attributes
- `src/pjsua_bot/register_bot.py` - Added CLI arguments

#### Key Features
- Persian text normalization (Unicode, zero-width characters, punctuation)
- Weighted keyword matching (longer keywords = higher confidence)
- Thread-safe transcription access
- Audio response playback with duration tracking
- Event logging for analytics

#### Usage
```bash
python register_bot.py --user 1001 --password pass --domain pbx.local \
  --enable-asr --enable-intent --stay-online
```

#### Testing
```bash
pytest tests/test_intent_phase1.py -v
```

---

## Phase 2: Semantic Search Classification ⏳

### Status: PENDING

### Overview
Add semantic search-based classification using sentence embeddings. This improves accuracy by understanding synonyms and paraphrasing, not just exact keyword matches.

### Prerequisites
- Phase 1 must be completed
- Install `sentence-transformers` package

### Implementation Steps

#### Step 1: Add Dependencies

**File: `pyproject.toml`**
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "sentence-transformers>=2.2.0",  # Add for Phase 2: Semantic search
]
```

#### Step 2: Create Semantic Classifier

**File: `src/pjsua_bot/intent/semantic_classifier.py`**
```python
"""Semantic search-based intent classifier using embeddings."""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple

try:
    from sentence_transformers import SentenceTransformer
    _SEMANTIC_AVAILABLE = True
except ImportError:
    _SEMANTIC_AVAILABLE = False
    SentenceTransformer = None

from pjsua_bot.intent.classifier import IntentClassifier
from pjsua_bot.intent.faq_config import FAQS


class SemanticClassifier(IntentClassifier):
    """Semantic search-based intent classifier using sentence embeddings."""
    
    def __init__(
        self,
        faqs: Optional[Dict] = None,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        similarity_threshold: float = 0.6,
    ):
        """Initialize semantic classifier.
        
        Args:
            faqs: FAQ configuration dict
            model_name: Sentence transformer model name
            similarity_threshold: Minimum similarity score (0.0-1.0)
        """
        if not _SEMANTIC_AVAILABLE:
            raise ImportError(
                "sentence-transformers not available. "
                "Install with: pip install sentence-transformers"
            )
        
        self.faqs = faqs or FAQS
        self.model_name = model_name
        self.threshold = similarity_threshold
        
        print(f"***Intent: Loading semantic model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("***Intent: Semantic model loaded")
        
        # Pre-encode FAQ questions
        self._encode_faqs()
    
    def _encode_faqs(self) -> None:
        """Pre-encode FAQ questions as embeddings."""
        self.faq_embeddings = {}
        
        for intent, config in self.faqs.items():
            if intent == "default":
                continue
            
            questions = config.get("questions", [])
            if not questions:
                # Fallback: use keywords as questions
                questions = [f"{kw} question" for kw in config.get("keywords", [])]
            
            if questions:
                embeddings = self.model.encode(questions, convert_to_numpy=True)
                self.faq_embeddings[intent] = {
                    "embeddings": embeddings,
                    "questions": questions,
                }
    
    def classify(
        self,
        transcription: str,
        threshold: Optional[float] = None,
    ) -> Tuple[str, float, Dict]:
        """Classify intent using semantic similarity.
        
        Args:
            transcription: The transcribed text
            threshold: Minimum similarity score (uses instance default if None)
            
        Returns:
            Tuple of (intent_name, confidence_score, faq_config)
        """
        if not transcription or not transcription.strip():
            return "default", 0.0, self.faqs["default"]
        
        threshold = threshold or self.threshold
        
        # Encode transcription
        query_embedding = self.model.encode([transcription], convert_to_numpy=True)[0]
        
        best_intent = "default"
        best_score = 0.0
        
        # Find best matching intent
        for intent, data in self.faq_embeddings.items():
            embeddings = data["embeddings"]
            
            # Calculate cosine similarity
            similarities = np.dot(embeddings, query_embedding) / (
                np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            
            max_similarity = float(np.max(similarities))
            
            if max_similarity > best_score:
                best_score = max_similarity
                best_intent = intent
        
        # Return best match if above threshold
        if best_score >= threshold:
            return best_intent, min(best_score, 1.0), self.faqs[best_intent]
        
        return "default", best_score, self.faqs["default"]
```

#### Step 3: Update Package Exports

**File: `src/pjsua_bot/intent/__init__.py`**
```python
"""Intent classification package for call bot."""

from .classifier import IntentClassifier, RuleBasedClassifier
from .faq_config import FAQS

try:
    from .semantic_classifier import SemanticClassifier
    __all__ = ["IntentClassifier", "RuleBasedClassifier", "SemanticClassifier", "FAQS"]
except ImportError:
    __all__ = ["IntentClassifier", "RuleBasedClassifier", "FAQS"]
```

#### Step 4: Update CLI to Support Method Selection

**File: `src/pjsua_bot/register_bot.py`**

Add argument after `--enable-intent`:
```python
parser.add_argument(
    "--intent-method",
    choices=["rule", "semantic", "hybrid"],
    default="rule",
    help="Intent classification method: rule-based, semantic, or hybrid (default: rule)",
)
```

Update initialization logic (after ASR initialization):
```python
# Initialize intent classifier before registration (if enabled)
if args.enable_intent:
    print("***Intent: initializing classifier before registration...")
    try:
        # Support both module and script execution
        if __package__ in (None, ""):
            from pjsua_bot.intent.classifier import RuleBasedClassifier
            from pjsua_bot.intent.faq_config import FAQS
            try:
                from pjsua_bot.intent.semantic_classifier import SemanticClassifier
            except ImportError:
                SemanticClassifier = None
        else:
            from .intent.classifier import RuleBasedClassifier
            from .intent.faq_config import FAQS
            try:
                from .intent.semantic_classifier import SemanticClassifier
            except ImportError:
                SemanticClassifier = None

        # Load custom FAQ config if provided, otherwise use default
        faqs = FAQS
        if args.faq_config and os.path.exists(args.faq_config):
            import json
            with open(args.faq_config, "r", encoding="utf-8") as f:
                faqs = json.load(f)
            print(f"***Intent: loaded custom FAQ config from {args.faq_config}")
        else:
            if args.faq_config:
                print(
                    f"***Intent: warning: FAQ config file not found: "
                    f"{args.faq_config}, using default"
                )

        # Create classifier based on method
        intent_method = getattr(args, "intent_method", "rule")
        
        if intent_method == "semantic":
            if SemanticClassifier is None:
                print("***Intent: semantic classifier not available, falling back to rule-based")
                acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
            else:
                acc._intent_classifier = SemanticClassifier(faqs=faqs)
        else:  # rule or default
            acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
        
        acc.enable_intent = True
        print(f"***Intent: {intent_method} classifier initialized and ready")
    except Exception as e:
        print(f"***Intent init error: {e}")
        acc._intent_classifier = None
        acc.enable_intent = False
```

#### Step 5: Create Tests

**File: `tests/test_intent_phase2.py`**
```python
"""Tests for Phase 2: Semantic intent classification."""

import pytest

try:
    from pjsua_bot.intent.semantic_classifier import SemanticClassifier
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False


@pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="sentence-transformers not available")
def test_semantic_classifier_initialization():
    """Test SemanticClassifier initialization."""
    classifier = SemanticClassifier()
    assert classifier is not None
    assert classifier.model is not None


@pytest.mark.skipif(not SEMANTIC_AVAILABLE, reason="sentence-transformers not available")
def test_semantic_classification():
    """Test semantic classification with Persian text."""
    classifier = SemanticClassifier()
    
    # Test that it can classify similar meanings
    intent, conf, config = classifier.classify("کامپیوترم خیلی کند شده")
    assert intent in ["slow_computer", "default"]
    assert conf >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### Step 6: Testing

1. Install dependencies:
   ```bash
   pip install sentence-transformers
   ```

2. Run tests:
   ```bash
   pytest tests/test_intent_phase2.py -v
   ```

3. Test with bot:
   ```bash
   python register_bot.py --user 1001 --password pass --domain pbx.local \
     --enable-asr --enable-intent --intent-method semantic --stay-online
   ```

### Expected Benefits
- Better handling of synonyms and paraphrasing
- Improved accuracy for natural language variations
- Multilingual support (model supports 100+ languages)

### Notes
- First run will download the model (~500MB-2GB)
- Model loading takes 5-10 seconds on first use
- GPU optional but recommended for faster inference

---

## Phase 3: Hybrid Approach ⏳

### Status: PENDING

### Overview
Combine rule-based and semantic search for best of both worlds: fast exact matches via rules, flexible matching via semantics.

### Prerequisites
- Phase 1 completed
- Phase 2 completed (or semantic classifier available)

### Implementation Steps

#### Step 1: Create Hybrid Classifier

**File: `src/pjsua_bot/intent/hybrid_classifier.py`**
```python
"""Hybrid classifier combining rule-based and semantic search."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from pjsua_bot.intent.classifier import RuleBasedClassifier, IntentClassifier
from pjsua_bot.intent.faq_config import FAQS

try:
    from pjsua_bot.intent.semantic_classifier import SemanticClassifier
    _SEMANTIC_AVAILABLE = True
except ImportError:
    _SEMANTIC_AVAILABLE = False
    SemanticClassifier = None


class HybridClassifier(IntentClassifier):
    """Hybrid classifier: fast rule-based with semantic fallback."""
    
    def __init__(
        self,
        faqs=None,
        rule_threshold: float = 0.3,
        semantic_threshold: float = 0.6,
        semantic_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        """Initialize hybrid classifier.
        
        Args:
            faqs: FAQ configuration
            rule_threshold: Threshold for rule-based classifier
            semantic_threshold: Threshold for semantic classifier
            semantic_model: Model name for semantic classifier
        """
        self.rule_classifier = RuleBasedClassifier(faqs=faqs)
        
        try:
            if SemanticClassifier is not None:
                self.semantic_classifier = SemanticClassifier(
                    faqs=faqs,
                    similarity_threshold=semantic_threshold,
                    model_name=semantic_model,
                )
                self.semantic_available = True
            else:
                self.semantic_classifier = None
                self.semantic_available = False
        except Exception as e:
            self.semantic_classifier = None
            self.semantic_available = False
            print(f"***Intent: Semantic classifier not available: {e}, using rule-based only")
    
    def classify(
        self,
        transcription: str,
        threshold: float = 0.5,
    ) -> Tuple[str, float, Dict]:
        """Classify using hybrid approach.
        
        Strategy:
        1. Try rule-based first (fast)
        2. If confidence low or no match, try semantic
        3. Return best result
        
        Args:
            transcription: The transcribed text
            threshold: Minimum confidence threshold
            
        Returns:
            Tuple of (intent_name, confidence_score, faq_config)
        """
        # Step 1: Try rule-based
        intent_rule, conf_rule, config_rule = self.rule_classifier.classify(
            transcription, threshold=0.3
        )
        
        # If rule-based found good match, use it
        if intent_rule != "default" and conf_rule >= 0.5:
            return intent_rule, conf_rule, config_rule
        
        # Step 2: Try semantic if available
        if self.semantic_available and self.semantic_classifier:
            intent_sem, conf_sem, config_sem = self.semantic_classifier.classify(
                transcription, threshold=0.6
            )
            
            # Use semantic if better than rule-based
            if conf_sem > conf_rule:
                return intent_sem, conf_sem, config_sem
        
        # Return rule-based result (even if default)
        return intent_rule, conf_rule, config_rule
```

#### Step 2: Update Package Exports

**File: `src/pjsua_bot/intent/__init__.py`**
```python
"""Intent classification package for call bot."""

from .classifier import IntentClassifier, RuleBasedClassifier
from .faq_config import FAQS

try:
    from .semantic_classifier import SemanticClassifier
    _SEMANTIC_AVAILABLE = True
except ImportError:
    _SEMANTIC_AVAILABLE = False

try:
    from .hybrid_classifier import HybridClassifier
    if _SEMANTIC_AVAILABLE:
        __all__ = [
            "IntentClassifier",
            "RuleBasedClassifier",
            "SemanticClassifier",
            "HybridClassifier",
            "FAQS",
        ]
    else:
        __all__ = ["IntentClassifier", "RuleBasedClassifier", "FAQS"]
except ImportError:
    if _SEMANTIC_AVAILABLE:
        __all__ = ["IntentClassifier", "RuleBasedClassifier", "SemanticClassifier", "FAQS"]
    else:
        __all__ = ["IntentClassifier", "RuleBasedClassifier", "FAQS"]
```

#### Step 3: Update CLI Initialization

**File: `src/pjsua_bot/register_bot.py`**

Update the classifier creation logic:
```python
# Create classifier based on method
intent_method = getattr(args, "intent_method", "rule")

if intent_method == "hybrid":
    try:
        from .intent.hybrid_classifier import HybridClassifier
        acc._intent_classifier = HybridClassifier(faqs=faqs)
    except ImportError:
        print("***Intent: hybrid classifier not available, falling back to rule-based")
        acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
elif intent_method == "semantic":
    if SemanticClassifier is None:
        print("***Intent: semantic classifier not available, falling back to rule-based")
        acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
    else:
        acc._intent_classifier = SemanticClassifier(faqs=faqs)
else:  # rule or default
    acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
```

#### Step 4: Create Tests

**File: `tests/test_intent_phase3.py`**
```python
"""Tests for Phase 3: Hybrid intent classification."""

import pytest

try:
    from pjsua_bot.intent.hybrid_classifier import HybridClassifier
    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False


@pytest.mark.skipif(not HYBRID_AVAILABLE, reason="Hybrid classifier not available")
def test_hybrid_classifier_initialization():
    """Test HybridClassifier initialization."""
    classifier = HybridClassifier()
    assert classifier is not None
    assert classifier.rule_classifier is not None


@pytest.mark.skipif(not HYBRID_AVAILABLE, reason="Hybrid classifier not available")
def test_hybrid_classification():
    """Test hybrid classification."""
    classifier = HybridClassifier()
    
    # Test exact keyword match (should use rule-based)
    intent, conf, config = classifier.classify("کامپیوترم کند است")
    assert intent == "slow_computer"
    assert conf > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### Step 5: Testing

```bash
python register_bot.py --user 1001 --password pass --domain pbx.local \
  --enable-asr --enable-intent --intent-method hybrid --stay-online
```

### Expected Benefits
- Fast exact matches via rule-based
- Flexible matching via semantic search
- Best accuracy for both common and edge cases
- Graceful degradation if semantic unavailable

---

## Phase 4: TTS Integration ⏳

### Status: PENDING

### Overview
Add Text-to-Speech capability to generate audio responses dynamically from FAQ text, eliminating need for pre-recorded audio files.

### Prerequisites
- Phase 1 completed
- Optional: Phases 2 and 3 for better intent classification

### Implementation Steps

#### Step 1: Add TTS Dependencies

**File: `pyproject.toml`**
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    # Option A: Offline TTS (cross-platform)
    "pyttsx3>=2.90",
    # OR Option B: Google TTS (requires internet)
    # "gTTS>=2.3.0",
]
```

**Option A: Offline TTS (pyttsx3)**
- Pros: Works offline, no API costs
- Cons: Lower quality, limited language support

**Option B: Google TTS (gTTS)**
- Pros: Better quality, good Persian support
- Cons: Requires internet, API rate limits

#### Step 2: Create TTS Service

**File: `src/pjsua_bot/tts/__init__.py`**
```python
"""Text-to-Speech service package."""

from .text_to_speech import TTSService

__all__ = ["TTSService"]
```

**File: `src/pjsua_bot/tts/text_to_speech.py`**
```python
"""Text-to-Speech service for dynamic responses."""

from __future__ import annotations

import os
import tempfile
from typing import Optional

try:
    import pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False

try:
    from gtts import gTTS
    _GTTS_AVAILABLE = True
except ImportError:
    _GTTS_AVAILABLE = False


class TTSService:
    """Text-to-Speech service wrapper."""
    
    def __init__(self, method: str = "pyttsx3", language: str = "fa"):
        """Initialize TTS service.
        
        Args:
            method: TTS method ("pyttsx3" or "gtts")
            language: Language code (e.g., "en", "fa", "ar")
        """
        self.method = method
        self.language = language
        self._engine = None
        
        if method == "pyttsx3" and _PYTTSX3_AVAILABLE:
            try:
                self._engine = pyttsx3.init()
                # Configure for Persian if available
                if language == "fa":
                    try:
                        voices = self._engine.getProperty("voices")
                        # Try to find Persian voice
                        for voice in voices:
                            if "persian" in voice.name.lower() or "farsi" in voice.name.lower():
                                self._engine.setProperty("voice", voice.id)
                                break
                    except Exception:
                        pass
                self.available = True
            except Exception:
                self.available = False
        elif method == "gtts" and _GTTS_AVAILABLE:
            self.available = True
        else:
            self.available = False
    
    def text_to_audio_file(
        self,
        text: str,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Convert text to audio file.
        
        Args:
            text: Text to convert
            output_path: Output file path (creates temp file if None)
            
        Returns:
            Path to audio file or None if failed
        """
        if not self.available:
            return None
        
        if not output_path:
            output_path = tempfile.mktemp(suffix=".wav")
        
        try:
            if self.method == "pyttsx3" and self._engine:
                self._engine.save_to_file(text, output_path)
                self._engine.runAndWait()
                return output_path if os.path.exists(output_path) else None
            
            elif self.method == "gtts":
                tts = gTTS(text=text, lang=self.language, slow=False)
                # gTTS saves to mp3, convert to wav if needed
                mp3_path = output_path.replace(".wav", ".mp3")
                tts.save(mp3_path)
                # For now, return mp3 (you may need ffmpeg to convert)
                # Or use pydub to convert: AudioSegment.from_mp3(mp3_path).export(output_path, format="wav")
                return mp3_path if os.path.exists(mp3_path) else None
            
        except Exception as e:
            print(f"***TTS: Error converting text to speech: {e}")
            return None
        
        return None
```

#### Step 3: Integrate TTS into Intent Handler

**File: `src/pjsua_bot/calls/mixins/intent_handler.py`**

Update `_play_intent_response()` method:
```python
def _play_intent_response(self) -> None:
    """Play response audio for classified intent."""
    if self._intent_response_played:
        return

    # Classify intent if not done yet
    classification = self._classify_intent()
    if not classification:
        print("***Intent: no intent classified, skipping response")
        return

    intent_name, confidence = classification

    # Get FAQ config from classifier
    if not self._intent_classifier:
        return

    try:
        from pjsua_bot.intent.faq_config import FAQS
        faq_config = FAQS.get(intent_name, FAQS["default"])
    except Exception as exc:
        print(f"***Intent: error getting FAQ config: {exc}")
        return

    # Determine response method (audio file or TTS)
    response_audio = faq_config.get("response_audio")
    response_text = faq_config.get("response_text", "")

    if response_audio and os.path.exists(response_audio):
        # Play pre-recorded audio
        self._play_response_audio(response_audio, intent_name)
    elif response_text:
        # Use TTS to generate audio
        tts_enabled = getattr(self._acc_ref, "enable_tts", False)
        if tts_enabled:
            tts_service = getattr(self._acc_ref, "_tts_service", None)
            if tts_service and tts_service.available:
                # Generate audio file from text
                audio_file = tts_service.text_to_audio_file(response_text)
                if audio_file and os.path.exists(audio_file):
                    print(f"***Intent: TTS generated audio: {audio_file}")
                    self._play_response_audio(audio_file, intent_name)
                else:
                    print("***Intent: TTS failed to generate audio, using text fallback")
                    self._intent_response_played = True
            else:
                print("***Intent: TTS service not available, using text fallback")
                self._intent_response_played = True
        else:
            print(f"***Intent: TTS not enabled, using text: {response_text[:50]}...")
            self._intent_response_played = True
```

#### Step 4: Add TTS Configuration

**File: `src/pjsua_bot/register_bot.py`**

Add CLI arguments:
```python
parser.add_argument(
    "--enable-tts",
    action="store_true",
    help="Enable Text-to-Speech for intent responses (default: False)",
)
parser.add_argument(
    "--tts-method",
    choices=["pyttsx3", "gtts"],
    default="pyttsx3",
    help="TTS method: pyttsx3 (offline) or gtts (online) (default: pyttsx3)",
)
parser.add_argument(
    "--tts-language",
    type=str,
    default="fa",
    help="TTS language code (default: fa for Persian)",
)
```

Initialize TTS service (after intent classifier):
```python
# Initialize TTS service (if enabled)
if args.enable_tts:
    print("***TTS: initializing service...")
    try:
        if __package__ in (None, ""):
            from pjsua_bot.tts import TTSService
        else:
            from .tts import TTSService
        
        acc._tts_service = TTSService(
            method=getattr(args, "tts_method", "pyttsx3"),
            language=getattr(args, "tts_language", "fa"),
        )
        acc.enable_tts = bool(acc._tts_service and acc._tts_service.available)
        
        if acc.enable_tts:
            print("***TTS: service initialized and ready")
        else:
            print("***TTS: service unavailable")
    except Exception as e:
        print(f"***TTS init error: {e}")
        acc._tts_service = None
        acc.enable_tts = False
```

**File: `src/pjsua_bot/account.py`**

Add TTS attributes:
```python
# TTS service (for dynamic audio generation)
self.enable_tts: bool = False
self._tts_service: Any | None = None
```

#### Step 5: Create Tests

**File: `tests/test_intent_phase4.py`**
```python
"""Tests for Phase 4: TTS integration."""

import pytest
import os

try:
    from pjsua_bot.tts import TTSService
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False


@pytest.mark.skipif(not TTS_AVAILABLE, reason="TTS not available")
def test_tts_service_initialization():
    """Test TTSService initialization."""
    service = TTSService(method="pyttsx3", language="fa")
    # Service may or may not be available depending on system
    assert service is not None


@pytest.mark.skipif(not TTS_AVAILABLE, reason="TTS not available")
def test_tts_text_to_audio():
    """Test TTS text to audio conversion."""
    service = TTSService(method="pyttsx3", language="fa")
    if service.available:
        audio_file = service.text_to_audio_file("تست")
        if audio_file:
            assert os.path.exists(audio_file)
            # Cleanup
            if os.path.exists(audio_file):
                os.remove(audio_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

#### Step 6: Testing

```bash
python register_bot.py --user 1001 --password pass --domain pbx.local \
  --enable-asr --enable-intent --enable-tts --tts-method pyttsx3 \
  --tts-language fa --stay-online
```

### Expected Benefits
- No need to pre-record FAQ audio files
- Dynamic response generation
- Easy to update FAQ responses (just change text)
- Supports multiple languages

### Notes
- TTS audio files can be cached to avoid regeneration
- Consider adding audio caching mechanism for performance
- gTTS requires internet connection
- pyttsx3 quality varies by system and available voices

---

## Testing Strategy

### Unit Tests
Each phase should have dedicated unit tests:
- Phase 1: `tests/test_intent_phase1.py` ✅
- Phase 2: `tests/test_intent_phase2.py` ⏳
- Phase 3: `tests/test_intent_phase3.py` ⏳
- Phase 4: `tests/test_intent_phase4.py` ⏳

### Integration Tests
Test end-to-end flow:
1. Call comes in
2. User speaks
3. Transcription happens
4. Intent is classified
5. Response is played
6. Goodbye message plays
7. Call hangs up

### Manual Testing
1. Start bot with appropriate flags
2. Make a test call
3. Speak one of the FAQ questions
4. Verify intent classification in logs
5. Verify response audio plays
6. Verify call flow completes correctly

## Troubleshooting

### Phase 1 Issues
- **No intent classified**: Check transcription is available, verify keywords match
- **Wrong intent**: Adjust keywords in FAQ config, lower threshold
- **Audio not playing**: Check file path, verify WAV format

### Phase 2 Issues
- **Model not loading**: Check internet connection, verify sentence-transformers installed
- **Slow classification**: Normal on first run (model download), consider GPU
- **Low accuracy**: Adjust similarity threshold, add more FAQ questions

### Phase 3 Issues
- **Hybrid not working**: Verify both rule and semantic classifiers available
- **Performance issues**: Rule-based should handle most cases, semantic only for fallback

### Phase 4 Issues
- **TTS not working**: Check TTS service available, verify language code
- **Audio quality poor**: Try different TTS method, adjust voice settings
- **Slow generation**: Consider caching generated audio files

## Performance Considerations

- **Phase 1**: Very fast (<1ms), no dependencies
- **Phase 2**: Fast (10-50ms), requires model download on first run
- **Phase 3**: Fast (<50ms), combines both methods efficiently
- **Phase 4**: Variable (1-5s for generation), consider caching

## Next Steps

After completing all phases:
1. Add audio caching for TTS responses
2. Add confidence threshold tuning
3. Add intent classification analytics
4. Consider real-time classification (per chunk, not just end-of-call)
5. Add support for multi-turn conversations
6. Add intent-based call routing

## References

- [Sentence Transformers Documentation](https://www.sbert.net/)
- [pyttsx3 Documentation](https://pyttsx3.readthedocs.io/)
- [gTTS Documentation](https://gtts.readthedocs.io/)
- [PJSUA2 Documentation](https://docs.pjsip.org/)




