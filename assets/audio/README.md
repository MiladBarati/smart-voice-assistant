# Audio assets manifest

This directory holds all pre-recorded WAV prompts the bot plays during calls.
Every WAV must be:

- 16-bit signed PCM
- mono
- 16 kHz sample rate (the bot also accepts 8 kHz; the `*_8k.wav` suffix is reserved
  for explicitly down-sampled assets)
- short and crisp — typical durations are 1.5 s – 6 s

## Conversation-flow prompts

### Shared / call lifecycle

| File | Purpose |
|---|---|
| `welcome_message.wav` | First message played when the bot answers an inbound call. |
| `goodbye_voice.wav` | Default goodbye played by `_play_goodbye_message()` before hangup. |
| `waiting_voice.wav` | Optional waiting tone for long-running operations. |

### Legacy flow (`--flow-mode legacy`)

| File | Spoken text (Persian) |
|---|---|
| `any_other_questions.wav` | "آیا سوال دیگه‌ای دارید؟ بله یا خیر." |
| `ask_next_question.wav` | "لطفاً سوال بعدی‌تون رو بفرمایید." |
| `repeat_or_support.wav` | "متاسفانه پاسخی ندارم. می‌خواهید دوباره بپرسید یا با پشتیبانی صحبت کنید؟" |
| `transferring_to_support.wav` | "در حال انتقال به پشتیبانی، لطفاً منتظر بمانید." |
| `max_retries_reached.wav` | "تعداد تماس‌ها به سقف رسید. خداحافظ." |

### Satisfaction flow (`--flow-mode satisfaction`)

These four files **must be recorded** before enabling `--flow-mode satisfaction` in
production. If any are missing the bot still completes the call — `_play_prompt()`
returns False, the state machine falls through to the safest available branch
(re-listen on retry, hang up on thank-you, hang up on escalation announcement) —
but the caller hears no audible cue for that step.

| File | Suggested Persian text | Suggested length |
|---|---|---|
| `satisfaction_prompt.wav` | "آیا این پاسخ به سوال شما کمک کرد؟ لطفاً بله یا خیر بفرمایید." | 3 – 4 s |
| `try_again_prompt.wav` | "متاسفم. لطفاً سوال‌تون رو با عبارت دیگه‌ای دوباره بفرمایید." | 3 – 4 s |
| `thank_you.wav` | "از تماس شما سپاسگزاریم. روز خوبی داشته باشید. خداحافظ." | 2 – 3 s |
| `escalation_announcement.wav` | "در حال انتقال تماس شما به یک کارشناس پشتیبانی هستم، لطفاً منتظر بمانید." | 3 – 4 s |

## FAQ answer prompts

Each entry under `FAQS` in `src/pjsua_bot/intent/faq_config.py` may reference a
`response_audio` WAV in this directory. The fallback for unrecognised questions
is `faq_default.wav`. See that file for the full list of FAQ audio files.

## Recording tips

- Record in a quiet room with a directional mic; trim leading/trailing silence
  to ≤ 100 ms.
- Normalise peaks to roughly -3 dBFS to keep playback consistent across files.
- Verify each file plays back correctly through PJSUA by running the bot with
  the matching CLI flag and `--enable-vad --enable-asr --enable-intent` enabled
  on a staging extension.
