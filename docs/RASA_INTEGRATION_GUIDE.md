# Rasa Integration Guide - 10 Phase Implementation Plan

This guide provides a step-by-step plan to integrate Rasa conversational AI framework into your PJSUA2 voice bot project.

## Overview

This integration plan allows you to:
- Gradually integrate Rasa without disrupting your current system
- Maintain your existing rule-based classifier as a fallback
- Test each phase independently
- Scale from simple intent classification to full conversational AI

## Prerequisites

- Python 3.11+
- Your existing PJSUA2 bot project
- Basic understanding of Rasa framework
- Docker (optional, for Phase 7+)

---

## Phase 1: Setup Rasa Environment (Standalone)

**Goal:** Install and test Rasa independently from your main project

### Steps

1. **Create a separate directory for Rasa project:**
   ```bash
   mkdir rasa-integration
   cd rasa-integration
   ```

2. **Install Rasa:**
   ```bash
   pip install rasa
   ```

3. **Initialize a new Rasa project:**
   ```bash
   rasa init --no-prompt
   ```

4. **Test Rasa works:**
   ```bash
   rasa shell
   # Type: "hello" to test
   ```

### Deliverable
✅ Working Rasa installation, can run `rasa shell` and get responses

### Verification
```bash
rasa --version
rasa shell
# Test with: "hello"
```

---

## Phase 2: Create Persian NLU Training Data

**Goal:** Convert your FAQ config to Rasa NLU training format

### Steps

1. **Create `data/nlu.yml` with your Persian intents:**

   ```yaml
   version: "3.1"
   
   nlu:
   - intent: slow_computer
     examples: |
       - کامپیوترم کند است
       - کامپیوتر کند کار می کند
       - کمبود رم دارم
       - برنامه های startup زیاد دارم
       - کامپیوترم کند
       - کند است
       - کند کار می کند
       - کند کار میکند
       - رم
       - کمبود رم
       - حافظه
       - دیسک
       - پاکسازی
       - پاکسازی دیسک
       - برنامه
       - برنامه های غیرضروری
       - برنامه‌های غیرضروری
       - سیستم عامل
       - سیستم‌عامل
       - آنتی ویروس
       - آنتی‌ویروس
       - به روزرسانی
       - به‌روزرسانی
       - آپدیت
       - ارتقا
       - ارتقا رم
   
   - intent: computer_shuts_down
     examples: |
       - کامپیوترم ناگهان خاموش می شود
       - کامپیوتر ناگهان خاموش می شود
       - کامپیوترم خاموش می شود
       - کامپیوتر خاموش می شود
       - ناگهان خاموش
       - خاموش می شود
       - خاموش میشود
       - خاموش
       - گرد و غبار
       - گردوغبار
       - فن
       - فن ها
       - فن‌ها
       - گرمای بیش از حد
       - گرما
       - گرم
       - تمیز
       - تمیز کردن
       - تمیزکردن
       - جریان هوا
       - جریان‌هوا
       - سخت افزار
       - سخت‌افزار
   
   - intent: screen_freezes
     examples: |
       - صفحه نمایش کامپیوترم فریز می شود
       - صفحه نمایش کامپیوتر فریز می شود
       - صفحه نمایش فریز می شود
       - برنامه گیر کرده
       - برنامه گیرکرده
       - برنامه‌های گیرکرده
       - صفحه فریز شده
       - کامپیوتر فریز می کند
       - فریز می شود
       - فریز میشود
       - صفحه نمایش
       - صفحه‌نمایش
       - فریز
       - Manager Task
       - Task Manager
       - تسک منیجر
       - برنامه
       - برنامه های گیرکرده
       - برنامه‌های گیرکرده
       - ریستارت
       - ریست
       - راه‌اندازی مجدد
       - نرمافزار
       - نرم‌افزار
       - به روزرسانی
       - به‌روزرسانی
       - تکرار
       - جلوگیری
   
   - intent: blue_screen
     examples: |
       - صفحه آبی مرگ ظاهر می شود
       - صفحه آبی مرگ
       - صفحه آبی
       - صفحه‌آبی
       - BSOD
       - Blue Screen
       - کد خطا
       - کد‌خطا
       - درایور
       - درایورها
       - به روزرسانی
       - به‌روزرسانی
       - اسکن
       - اسکن سیستم
       - سخت افزار
       - سخت‌افزار
       - تکنسین
       - تعمیرکار
   
   - intent: slow_internet
     examples: |
       - اینترنت کند کار می کند
       - اینترنت کند کار میکند
       - اینترنت من کند است
       - اینترنت کند
       - اینترنت من کند
       - اینترنت
       - کند است
       - کند
       - کش
       - کش مرورگر
       - کش‌مرورگر
       - مرورگر
       - بروزر
       - پاک
       - پاک کردن
       - پاککردن
       - اکستنشن
       - اکستنشن های غیرضروری
       - اکستنشن‌های غیرضروری
       - روتر
       - مودم
       - ریستارت
       - ریست
       - سرعت
       - سرعت اینترنت
       - تست سرعت
       - ISP
       - سرویس دهنده
   
   - intent: nlu_fallback
     examples: |
       - سلام
       - خداحافظ
       - متشکرم
       - بله
       - خیر
   ```

2. **Train the NLU model:**
   ```bash
   rasa train nlu
   ```

3. **Test NLU:**
   ```bash
   rasa shell nlu
   # Test: "کامپیوترم کند است"
   ```

### Deliverable
✅ Rasa NLU model trained on your Persian FAQs

### Verification
```bash
rasa test nlu
# Should show intent classification results
```

---

## Phase 3: Create Rasa HTTP API Service

**Goal:** Run Rasa as an HTTP API service that your bot can call

### Steps

1. **Start Rasa server:**
   ```bash
   rasa run --enable-api --cors "*" --port 5005
   ```

2. **Test API endpoint:**
   ```bash
   curl -X POST http://localhost:5005/model/parse \
     -H "Content-Type: application/json" \
     -d '{"text": "کامپیوترم کند است"}'
   ```

3. **Create a simple Python client to test:**
   
   Create `test_rasa_client.py`:
   ```python
   # test_rasa_client.py
   import requests
   
   def test_rasa(text: str):
       response = requests.post(
           "http://localhost:5005/model/parse",
           json={"text": text}
       )
       return response.json()
   
   if __name__ == "__main__":
       result = test_rasa("کامپیوترم کند است")
       print(result)
   ```

   Run it:
   ```bash
   python test_rasa_client.py
   ```

### Deliverable
✅ Rasa running as HTTP API, can query from Python

### Verification
```bash
# Check Rasa is running
curl http://localhost:5005/status

# Test parse endpoint
curl -X POST http://localhost:5005/model/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "کامپیوترم کند است"}'
```

---

## Phase 4: Create Rasa Client Wrapper

**Goal:** Create a Python wrapper class to interface with Rasa API

### Steps

1. **Create `src/pjsua_bot/intent/rasa_client.py`:**

   ```python
   """Rasa NLU client wrapper."""
   
   from __future__ import annotations
   
   import requests
   from typing import Dict, Optional
   
   class RasaClient:
       """Client for Rasa NLU HTTP API."""
       
       def __init__(self, base_url: str = "http://localhost:5005"):
           """Initialize Rasa client.
           
           Args:
               base_url: Base URL of Rasa server
           """
           self.base_url = base_url
           self.available = False
           self._check_availability()
       
       def _check_availability(self) -> None:
           """Check if Rasa server is available."""
           try:
               response = requests.get(
                   f"{self.base_url}/status",
                   timeout=2
               )
               self.available = response.status_code == 200
               if self.available:
                   print(f"***Rasa: Server available at {self.base_url}")
           except Exception as e:
               print(f"***Rasa: Server unavailable: {e}")
               self.available = False
       
       def parse(self, text: str) -> Optional[Dict]:
           """Parse text using Rasa NLU.
           
           Args:
               text: Text to parse
               
           Returns:
               Rasa parse result or None if unavailable
           """
           if not self.available or not text:
               return None
           
           try:
               response = requests.post(
                   f"{self.base_url}/model/parse",
                   json={"text": text},
                   timeout=1.0  # Fast timeout for real-time
               )
               if response.status_code == 200:
                   return response.json()
               else:
                   print(f"***Rasa: API returned status {response.status_code}")
           except requests.exceptions.Timeout:
               print("***Rasa: API timeout")
               self.available = False
           except Exception as e:
               print(f"***Rasa: API error: {e}")
               self.available = False
           
           return None
   ```

2. **Test the wrapper:**
   
   Create `test_rasa_wrapper.py`:
   ```python
   from src.pjsua_bot.intent.rasa_client import RasaClient
   
   client = RasaClient()
   print(f"Available: {client.available}")
   
   if client.available:
       result = client.parse("کامپیوترم کند است")
       print(result)
   ```

### Deliverable
✅ Python wrapper class for Rasa API

### Verification
```python
from src.pjsua_bot.intent.rasa_client import RasaClient

client = RasaClient()
assert client.available == True
result = client.parse("کامپیوترم کند است")
assert result is not None
assert "intent" in result
```

---

## Phase 5: Create Rasa Classifier Adapter

**Goal:** Create a classifier that implements your IntentClassifier interface but uses Rasa

### Steps

1. **Create `src/pjsua_bot/intent/rasa_classifier.py`:**

   ```python
   """Rasa-based intent classifier."""
   
   from __future__ import annotations
   
   from typing import Dict, Optional, Tuple
   
   from pjsua_bot.intent.classifier import IntentClassifier
   from pjsua_bot.intent.faq_config import FAQS
   from pjsua_bot.intent.rasa_client import RasaClient
   
   class RasaClassifier(IntentClassifier):
       """Intent classifier using Rasa NLU."""
       
       def __init__(
           self,
           faqs: Optional[Dict] = None,
           rasa_url: str = "http://localhost:5005",
           fallback_to_rule: bool = True,
       ):
           """Initialize Rasa classifier.
           
           Args:
               faqs: FAQ configuration (for response mapping)
               rasa_url: Rasa server URL
               fallback_to_rule: Use rule-based if Rasa unavailable
           """
           self.faqs = faqs or FAQS
           self.rasa_client = RasaClient(base_url=rasa_url)
           self.fallback_to_rule = fallback_to_rule
           
           # Import rule-based as fallback
           if fallback_to_rule:
               from pjsua_bot.intent.classifier import RuleBasedClassifier
               self.rule_classifier = RuleBasedClassifier(faqs=faqs)
               print("***Rasa: Rule-based fallback enabled")
           else:
               self.rule_classifier = None
           
           if self.rasa_client.available:
               print("***Rasa: Classifier initialized with Rasa NLU")
           else:
               print("***Rasa: Classifier initialized with rule-based fallback only")
       
       def classify(
           self,
           transcription: str,
           threshold: float = 0.5,
       ) -> Tuple[str, float, Dict]:
           """Classify intent using Rasa, with fallback to rule-based.
           
           Args:
               transcription: The transcribed text
               threshold: Confidence threshold
               
           Returns:
               Tuple of (intent_name, confidence_score, faq_config)
           """
           # Try Rasa first
           if self.rasa_client.available:
               rasa_result = self.rasa_client.parse(transcription)
               if rasa_result:
                   intent_name = rasa_result.get("intent", {}).get("name")
                   confidence = rasa_result.get("intent", {}).get("confidence", 0.0)
                   
                   # Check if intent is valid and above threshold
                   if intent_name and intent_name != "nlu_fallback":
                       if intent_name in self.faqs:
                           if confidence >= threshold:
                               print(
                                   f"***Rasa: classified as '{intent_name}' "
                                   f"(confidence: {confidence:.2f})"
                               )
                               return intent_name, confidence, self.faqs[intent_name]
                           else:
                               print(
                                   f"***Rasa: confidence {confidence:.2f} below "
                                   f"threshold {threshold}, falling back"
                               )
           
           # Fallback to rule-based
           if self.fallback_to_rule and self.rule_classifier:
               print("***Rasa: falling back to rule-based classifier")
               return self.rule_classifier.classify(transcription, threshold)
           
           # Final fallback
           print("***Rasa: using default intent")
           return "default", 0.0, self.faqs["default"]
   ```

2. **Update `src/pjsua_bot/intent/__init__.py`:**

   ```python
   """Intent classification package for call bot."""
   
   from .classifier import IntentClassifier, RuleBasedClassifier
   from .faq_config import FAQS
   
   try:
       from .rasa_classifier import RasaClassifier
       __all__ = [
           "IntentClassifier",
           "RuleBasedClassifier",
           "RasaClassifier",
           "FAQS",
       ]
   except ImportError:
       __all__ = ["IntentClassifier", "RuleBasedClassifier", "FAQS"]
   ```

### Deliverable
✅ RasaClassifier that implements your interface with fallback

### Verification
```python
from src.pjsua_bot.intent.rasa_classifier import RasaClassifier

classifier = RasaClassifier()
intent, conf, config = classifier.classify("کامپیوترم کند است")
assert intent == "slow_computer"
assert conf > 0.5
```

---

## Phase 6: Add Rasa Option to CLI

**Goal:** Allow users to choose Rasa as intent classification method

### Steps

1. **Update `src/pjsua_bot/register_bot.py`:**

   Add to argument parser:
   ```python
   parser.add_argument(
       "--intent-method",
       choices=["rule", "semantic", "hybrid", "rasa"],
       default="rule",
       help="Intent classification method: rule-based, semantic, hybrid, or rasa (default: rule)",
   )
   parser.add_argument(
       "--rasa-url",
       type=str,
       default="http://localhost:5005",
       help="Rasa server URL (default: http://localhost:5005)",
   )
   ```

   Update initialization section (after ASR init):
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
                   from pjsua_bot.intent.rasa_classifier import RasaClassifier
               except ImportError:
                   RasaClassifier = None
           else:
               from .intent.classifier import RuleBasedClassifier
               from .intent.faq_config import FAQS
               try:
                   from .intent.rasa_classifier import RasaClassifier
               except ImportError:
                   RasaClassifier = None

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
           
           if intent_method == "rasa":
               if RasaClassifier is None:
                   print("***Intent: Rasa not available, falling back to rule-based")
                   acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
               else:
                   rasa_url = getattr(args, "rasa_url", "http://localhost:5005")
                   acc._intent_classifier = RasaClassifier(
                       faqs=faqs,
                       rasa_url=rasa_url,
                       fallback_to_rule=True,
                   )
                   if acc._intent_classifier.rasa_client.available:
                       print("***Intent: Rasa classifier initialized and ready")
                   else:
                       print("***Intent: Rasa unavailable, using rule-based fallback")
           elif intent_method == "semantic":
               # Existing semantic logic
               # ... (keep your existing code)
               acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
           elif intent_method == "hybrid":
               # Existing hybrid logic
               # ... (keep your existing code)
               acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
           else:  # rule or default
               acc._intent_classifier = RuleBasedClassifier(faqs=faqs)
           
           acc.enable_intent = True
           print(f"***Intent: {intent_method} classifier initialized")
       except Exception as e:
           print(f"***Intent init error: {e}")
           acc._intent_classifier = None
           acc.enable_intent = False
   ```

### Deliverable
✅ CLI option to use Rasa classifier

### Verification
```bash
# Start Rasa server first
cd rasa-integration
rasa run --enable-api --cors "*" --port 5005

# In another terminal, test your bot
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password pass \
  --domain pbx.local \
  --enable-asr \
  --enable-intent \
  --intent-method rasa \
  --rasa-url http://localhost:5005 \
  --stay-online
```

---

## Phase 7: Dockerize Rasa Service

**Goal:** Run Rasa in Docker for easier deployment

### Steps

1. **Create `rasa-integration/Dockerfile`:**

   ```dockerfile
   FROM rasa/rasa:3.6.0-full
   
   WORKDIR /app
   COPY . /app
   
   USER root
   RUN rasa train
   
   USER 1001
   CMD ["run", "--enable-api", "--cors", "*", "--port", "5005"]
   ```

2. **Create `rasa-integration/docker-compose.yml`:**

   ```yaml
   version: '3.8'
   
   services:
     rasa:
       build: .
       ports:
         - "5005:5005"
       volumes:
         - ./models:/app/models
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:5005/status"]
         interval: 30s
         timeout: 10s
         retries: 3
       restart: unless-stopped
   ```

3. **Update your main `docker-compose.yml` to include Rasa:**

   ```yaml
   version: '3.8'
   
   services:
     # ... existing services ...
     
     rasa:
       build: ./rasa-integration
       ports:
         - "5005:5005"
       networks:
         - pjsua-network
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:5005/status"]
         interval: 30s
         timeout: 10s
         retries: 3
       restart: unless-stopped
   
     pjsua-bot:
       # ... existing config ...
       depends_on:
         - rasa
       environment:
         - RASA_URL=http://rasa:5005
       networks:
         - pjsua-network
   
   networks:
     pjsua-network:
       driver: bridge
   ```

### Deliverable
✅ Rasa running in Docker, accessible to your bot

### Verification
```bash
# Build and start Rasa
cd rasa-integration
docker-compose up -d

# Check status
curl http://localhost:5005/status

# Test parse
curl -X POST http://localhost:5005/model/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "کامپیوترم کند است"}'
```

---

## Phase 8: Add Health Checks and Retry Logic

**Goal:** Make Rasa integration robust with proper error handling

### Steps

1. **Enhance `RasaClient` with retry logic:**

   Update `src/pjsua_bot/intent/rasa_client.py`:
   ```python
   """Rasa NLU client wrapper with retry logic."""
   
   from __future__ import annotations
   
   import time
   import requests
   from typing import Dict, Optional
   
   class RasaClient:
       """Client for Rasa NLU HTTP API with retry logic."""
       
       def __init__(
           self,
           base_url: str = "http://localhost:5005",
           max_retries: int = 2,
           retry_delay: float = 0.1,
       ):
           """Initialize Rasa client.
           
           Args:
               base_url: Base URL of Rasa server
               max_retries: Maximum retry attempts
               retry_delay: Delay between retries in seconds
           """
           self.base_url = base_url
           self.max_retries = max_retries
           self.retry_delay = retry_delay
           self.available = False
           self._check_availability()
       
       def _check_availability(self) -> None:
           """Check if Rasa server is available."""
           try:
               response = requests.get(
                   f"{self.base_url}/status",
                   timeout=2
               )
               self.available = response.status_code == 200
               if self.available:
                   print(f"***Rasa: Server available at {self.base_url}")
           except Exception as e:
               print(f"***Rasa: Server unavailable: {e}")
               self.available = False
       
       def parse(self, text: str) -> Optional[Dict]:
           """Parse text using Rasa NLU with retry logic.
           
           Args:
               text: Text to parse
               
           Returns:
               Rasa parse result or None if unavailable
           """
           if not text:
               return None
           
           for attempt in range(self.max_retries + 1):
               try:
                   response = requests.post(
                       f"{self.base_url}/model/parse",
                       json={"text": text},
                       timeout=1.0,  # Fast timeout for real-time
                   )
                   if response.status_code == 200:
                       self.available = True
                       return response.json()
                   else:
                       print(
                           f"***Rasa: API returned status {response.status_code} "
                           f"(attempt {attempt + 1}/{self.max_retries + 1})"
                       )
               except requests.exceptions.Timeout:
                   if attempt < self.max_retries:
                       time.sleep(self.retry_delay)
                       continue
                   print(f"***Rasa: API timeout after {attempt + 1} attempts")
                   self.available = False
               except requests.exceptions.RequestException as e:
                   if attempt < self.max_retries:
                       time.sleep(self.retry_delay)
                       continue
                   print(f"***Rasa: API error after {attempt + 1} attempts: {e}")
                   self.available = False
           
           return None
   ```

2. **Add periodic health checks in `RasaClassifier`:**

   Update `src/pjsua_bot/intent/rasa_classifier.py`:
   ```python
   """Rasa-based intent classifier with health checks."""
   
   from __future__ import annotations
   
   import threading
   import time
   from typing import Dict, Optional, Tuple
   
   from pjsua_bot.intent.classifier import IntentClassifier
   from pjsua_bot.intent.faq_config import FAQS
   from pjsua_bot.intent.rasa_client import RasaClient
   
   class RasaClassifier(IntentClassifier):
       """Intent classifier using Rasa NLU with health monitoring."""
       
       def __init__(
           self,
           faqs: Optional[Dict] = None,
           rasa_url: str = "http://localhost:5005",
           fallback_to_rule: bool = True,
           health_check_interval: int = 30,
       ):
           """Initialize Rasa classifier.
           
           Args:
               faqs: FAQ configuration (for response mapping)
               rasa_url: Rasa server URL
               fallback_to_rule: Use rule-based if Rasa unavailable
               health_check_interval: Health check interval in seconds
           """
           self.faqs = faqs or FAQS
           self.rasa_client = RasaClient(base_url=rasa_url)
           self.fallback_to_rule = fallback_to_rule
           self.health_check_interval = health_check_interval
           
           # Import rule-based as fallback
           if fallback_to_rule:
               from pjsua_bot.intent.classifier import RuleBasedClassifier
               self.rule_classifier = RuleBasedClassifier(faqs=faqs)
               print("***Rasa: Rule-based fallback enabled")
           else:
               self.rule_classifier = None
           
           if self.rasa_client.available:
               print("***Rasa: Classifier initialized with Rasa NLU")
           else:
               print("***Rasa: Classifier initialized with rule-based fallback only")
           
           # Start background health check
           self._health_check_thread = None
           self._start_health_check()
       
       def _start_health_check(self):
           """Start background health check thread."""
           def check():
               while True:
                   time.sleep(self.health_check_interval)
                   was_available = self.rasa_client.available
                   self.rasa_client._check_availability()
                   if was_available != self.rasa_client.available:
                       if self.rasa_client.available:
                           print("***Rasa: Server recovered")
                       else:
                           print("***Rasa: Server unavailable, using fallback")
           
           self._health_check_thread = threading.Thread(
               target=check,
               daemon=True
           )
           self._health_check_thread.start()
       
       def classify(
           self,
           transcription: str,
           threshold: float = 0.5,
       ) -> Tuple[str, float, Dict]:
           """Classify intent using Rasa, with fallback to rule-based.
           
           Args:
               transcription: The transcribed text
               threshold: Confidence threshold
               
           Returns:
               Tuple of (intent_name, confidence_score, faq_config)
           """
           # Try Rasa first
           if self.rasa_client.available:
               rasa_result = self.rasa_client.parse(transcription)
               if rasa_result:
                   intent_name = rasa_result.get("intent", {}).get("name")
                   confidence = rasa_result.get("intent", {}).get("confidence", 0.0)
                   
                   # Check if intent is valid and above threshold
                   if intent_name and intent_name != "nlu_fallback":
                       if intent_name in self.faqs:
                           if confidence >= threshold:
                               print(
                                   f"***Rasa: classified as '{intent_name}' "
                                   f"(confidence: {confidence:.2f})"
                               )
                               return intent_name, confidence, self.faqs[intent_name]
                           else:
                               print(
                                   f"***Rasa: confidence {confidence:.2f} below "
                                   f"threshold {threshold}, falling back"
                               )
           
           # Fallback to rule-based
           if self.fallback_to_rule and self.rule_classifier:
               print("***Rasa: falling back to rule-based classifier")
               return self.rule_classifier.classify(transcription, threshold)
           
           # Final fallback
           print("***Rasa: using default intent")
           return "default", 0.0, self.faqs["default"]
   ```

### Deliverable
✅ Robust Rasa client with retry and health checks

### Verification
```python
# Test retry logic by temporarily stopping Rasa
# Should fallback gracefully and recover when Rasa restarts
```

---

## Phase 9: Add Rasa Stories for Multi-turn (Optional)

**Goal:** Enable multi-turn conversations if needed

### Steps

1. **Create `data/stories.yml`:**

   ```yaml
   version: "3.1"
   
   stories:
   - story: slow computer followup
     steps:
     - intent: slow_computer
     - action: utter_slow_computer_response
     - intent: ask_question
     - action: utter_further_help
   
   - story: computer shuts down followup
     steps:
     - intent: computer_shuts_down
     - action: utter_computer_shuts_down_response
     - intent: ask_question
     - action: utter_further_help
   
   - story: screen freezes followup
     steps:
     - intent: screen_freezes
     - action: utter_screen_freezes_response
     - intent: ask_question
     - action: utter_further_help
   ```

2. **Create `data/responses.yml`:**

   ```yaml
   version: "3.1"
   
   responses:
     utter_slow_computer_response:
       - text: "علت اغلب کمبود رم، برنامه های startup زیاد یا malware است. دیسک را پاکسازی کنید، برنامه های غیرضروری را ببندید، سیستم عامل و آنتی ویروس را به روزرسانی کنید و رم را ارتقا دهید."
   
     utter_computer_shuts_down_response:
       - text: "معمولاً به دلیل گرد و غبار در فن ها یا گرمای بیش از حد است. فنها را تمیز کنید، جریان هوا را بررسی کنید و اگر ادامه داشت، سخت افزار را چک کنید."
   
     utter_screen_freezes_response:
       - text: "از Manager Task برای بستن برنامه های گیرکرده استفاده کنید یا سیستم را ریستارت کنید. نرمافزارها را به روزرسانی کنید تا از تکرار جلوگیری شود."
   
     utter_further_help:
       - text: "آیا سوال دیگری دارید؟"
   ```

3. **Create `domain.yml`:**

   ```yaml
   version: "3.1"
   
   intents:
     - slow_computer
     - computer_shuts_down
     - screen_freezes
     - blue_screen
     - slow_internet
     - nlu_fallback
     - ask_question
   
   responses:
     utter_slow_computer_response:
       - text: "علت اغلب کمبود رم، برنامه های startup زیاد یا malware است..."
     utter_computer_shuts_down_response:
       - text: "معمولاً به دلیل گرد و غبار در فن ها یا گرمای بیش از حد است..."
     utter_screen_freezes_response:
       - text: "از Manager Task برای بستن برنامه های گیرکرده استفاده کنید..."
     utter_further_help:
       - text: "آیا سوال دیگری دارید؟"
   ```

4. **Train full Rasa model:**
   ```bash
   rasa train
   ```

5. **Update your integration to handle multi-turn (if needed):**

   Update `RasaClient` to support conversations:
   ```python
   def parse(self, text: str, conversation_id: str = None) -> Optional[Dict]:
       """Parse text, optionally with conversation context."""
       if not self.available or not text:
           return None
       
       url = f"{self.base_url}/model/parse"
       if conversation_id:
           url = f"{self.base_url}/conversations/{conversation_id}/parse"
       
       try:
           response = requests.post(
               url,
               json={"text": text},
               timeout=1.0,
           )
           if response.status_code == 200:
               return response.json()
       except Exception as e:
           print(f"***Rasa: API error: {e}")
           self.available = False
       
       return None
   ```

### Deliverable
✅ Multi-turn conversation support (if needed)

### Verification
```bash
# Test multi-turn
rasa shell
# Type: "کامپیوترم کند است"
# Then: "بله"
```

---

## Phase 10: Performance Optimization & Production Setup

**Goal:** Optimize for production use

### Steps

1. **Add response caching:**

   Update `RasaClassifier`:
   ```python
   from functools import lru_cache
   from hashlib import md5
   import time
   
   class RasaClassifier(IntentClassifier):
       def __init__(self, ...):
           # ... existing init ...
           self._cache = {}
           self._cache_ttl = 300  # 5 minutes
       
       def classify(self, transcription: str, threshold: float = 0.5, ...):
           # Cache key
           cache_key = md5(transcription.encode()).hexdigest()
           
           # Check cache
           if cache_key in self._cache:
               cached_time, cached_result = self._cache[cache_key]
               if time.time() - cached_time < self._cache_ttl:
                   print("***Rasa: using cached result")
                   return cached_result
               else:
                   # Expired, remove from cache
                   del self._cache[cache_key]
           
           # ... existing classification logic ...
           
           # Cache result
           self._cache[cache_key] = (time.time(), (intent_name, confidence, faq_config))
           
           # Clean old cache entries
           if len(self._cache) > 1000:
               self._clean_cache()
           
           return intent_name, confidence, faq_config
       
       def _clean_cache(self):
           """Remove expired cache entries."""
           current_time = time.time()
           expired_keys = [
               key for key, (cached_time, _) in self._cache.items()
               if current_time - cached_time >= self._cache_ttl
           ]
           for key in expired_keys:
               del self._cache[key]
   ```

2. **Add metrics/logging:**

   Update `RasaClassifier.classify()`:
   ```python
   def classify(self, transcription: str, threshold: float = 0.5, ...):
       start_time = time.time()
       
       # ... existing classification logic ...
       
       duration = time.time() - start_time
       
       # Log metrics (if _collect_event available)
       if hasattr(self, '_collect_event'):
           try:
               self._collect_event(
                   event_type="rasa_classification",
                   duration=duration,
                   intent=intent_name,
                   confidence=confidence,
                   transcription_length=len(transcription),
               )
           except Exception:
               pass
       
       return intent_name, confidence, faq_config
   ```

3. **Create production deployment script:**

   Create `scripts/deploy_rasa.sh`:
   ```bash
   #!/bin/bash
   # deploy_rasa.sh
   
   set -e
   
   echo "Building Rasa Docker image..."
   cd rasa-integration
   docker-compose build
   
   echo "Starting Rasa service..."
   docker-compose up -d
   
   echo "Waiting for Rasa to be ready..."
   sleep 10
   
   echo "Checking Rasa health..."
   for i in {1..30}; do
       if curl -f http://localhost:5005/status > /dev/null 2>&1; then
           echo "Rasa is ready!"
           exit 0
       fi
       echo "Waiting for Rasa... ($i/30)"
       sleep 2
   done
   
   echo "Rasa failed to start"
   exit 1
   ```

   Make it executable:
   ```bash
   chmod +x scripts/deploy_rasa.sh
   ```

4. **Add to your main deployment:**

   Update `docker-compose.yml`:
   ```yaml
   version: '3.8'
   
   services:
     rasa:
       build: ./rasa-integration
       ports:
         - "5005:5005"
       networks:
         - pjsua-network
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:5005/status"]
         interval: 30s
         timeout: 10s
         retries: 3
       restart: unless-stopped
       environment:
         - RASA_ENVIRONMENT=production
   
     pjsua-bot:
       # ... existing config ...
       depends_on:
         rasa:
           condition: service_healthy
       environment:
         - RASA_URL=http://rasa:5005
       networks:
         - pjsua-network
   
   networks:
     pjsua-network:
       driver: bridge
   ```

5. **Create monitoring script:**

   Create `scripts/monitor_rasa.py`:
   ```python
   #!/usr/bin/env python3
   """Monitor Rasa service health."""
   
   import requests
   import sys
   import time
   
   RASA_URL = "http://localhost:5005"
   
   def check_rasa():
       try:
           response = requests.get(f"{RASA_URL}/status", timeout=2)
           if response.status_code == 200:
               data = response.json()
               print(f"Rasa Status: OK")
               print(f"Model: {data.get('model_file', 'N/A')}")
               return True
           else:
               print(f"Rasa Status: ERROR (HTTP {response.status_code})")
               return False
       except Exception as e:
           print(f"Rasa Status: UNAVAILABLE ({e})")
           return False
   
   if __name__ == "__main__":
       if not check_rasa():
           sys.exit(1)
   ```

### Deliverable
✅ Production-ready Rasa integration with caching and monitoring

### Verification
```bash
# Deploy
./scripts/deploy_rasa.sh

# Monitor
python scripts/monitor_rasa.py

# Test with bot
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password pass \
  --domain pbx.local \
  --enable-asr \
  --enable-intent \
  --intent-method rasa \
  --stay-online
```

---

## Testing Checklist for Each Phase

- ✅ **Phase 1:** Rasa shell works
- ✅ **Phase 2:** NLU recognizes Persian intents
- ✅ **Phase 3:** API responds correctly
- ✅ **Phase 4:** Python client works
- ✅ **Phase 5:** RasaClassifier returns correct intents
- ✅ **Phase 6:** CLI option works, fallback works
- ✅ **Phase 7:** Docker service accessible
- ✅ **Phase 8:** Retry logic handles failures
- ✅ **Phase 9:** Multi-turn works (if implemented)
- ✅ **Phase 10:** Performance acceptable, production-ready

---

## Usage Example (After Phase 6)

### Start Rasa Server

```bash
# Option 1: Direct
cd rasa-integration
rasa run --enable-api --cors "*" --port 5005

# Option 2: Docker
cd rasa-integration
docker-compose up -d
```

### Run Your Bot with Rasa

```bash
python -m src.pjsua_bot.register_bot \
  --user 1001 \
  --password pass \
  --domain pbx.local \
  --enable-asr \
  --enable-intent \
  --intent-method rasa \
  --rasa-url http://localhost:5005 \
  --stay-online
```

### Test Fallback Behavior

```bash
# Stop Rasa server
# Bot should automatically fallback to rule-based classifier
# Restart Rasa - bot should automatically recover
```

---

## Troubleshooting

### Rasa Server Not Available

**Symptoms:** Bot falls back to rule-based classifier

**Solutions:**
1. Check Rasa is running: `curl http://localhost:5005/status`
2. Check firewall/network settings
3. Verify `--rasa-url` matches actual Rasa URL
4. Check Rasa logs for errors

### Low Confidence Scores

**Symptoms:** Rasa returns intents but with low confidence

**Solutions:**
1. Add more training examples to `data/nlu.yml`
2. Retrain model: `rasa train nlu`
3. Adjust threshold in classifier
4. Review training data quality

### Slow Response Times

**Symptoms:** Intent classification takes too long

**Solutions:**
1. Enable caching (Phase 10)
2. Reduce `max_retries` in `RasaClient`
3. Use faster timeout values
4. Consider running Rasa on same machine/network

### Docker Issues

**Symptoms:** Rasa container fails to start

**Solutions:**
1. Check Docker logs: `docker-compose logs rasa`
2. Verify Dockerfile syntax
3. Check port 5005 is not in use
4. Ensure models directory has correct permissions

---

## Next Steps

After completing all phases:

1. **Add entity extraction** - Extract specific information from user input
2. **Implement custom actions** - Connect to external APIs/databases
3. **Add conversation analytics** - Track conversation quality
4. **Optimize training data** - Improve accuracy with more examples
5. **A/B testing** - Compare Rasa vs rule-based performance
6. **Multi-language support** - Add support for other languages

---

## References

- [Rasa Documentation](https://rasa.com/docs/)
- [Rasa NLU Training Data Format](https://rasa.com/docs/rasa/training-data-format)
- [Rasa HTTP API](https://rasa.com/docs/rasa/pages/http-api)
- [Rasa Docker Deployment](https://rasa.com/docs/rasa/docker/deploying-in-docker)

---

## Summary

This 10-phase plan allows you to:
- ✅ Gradually integrate Rasa without disrupting your current system
- ✅ Maintain your existing rule-based classifier as a fallback
- ✅ Test each phase independently
- ✅ Scale from simple intent classification to full conversational AI
- ✅ Deploy in production with proper error handling and monitoring

Each phase builds on the previous one, allowing you to stop at any point and still have a working system.

