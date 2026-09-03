# Custom Voice Directory for Ultron

You can customize Ultron's voice using two methods:

---

## Method 1: Instant Pre-Built Neural Voices (Recommended)
You can change the voice immediately by editing `config.yaml`:
```yaml
audio:
  tts_voice: "en-GB-RyanNeural"       # Jarvis British Accent
  # tts_voice: "en-US-BrianNeural"     # Deep Cinematic Ultron
  # tts_voice: "en-US-JennyNeural"     # Siri / Friday Female
  # tts_voice: "en-IN-PrabhatNeural"   # Indian English Male
  tts_pitch: "-4Hz"                   # Adjust pitch (e.g. -8Hz for deeper robotic tone)
  tts_rate: "+5%"                     # Adjust speed
```

---

## Method 2: Upload Your Own Audio File (Voice Cloning)
If you want Ultron to speak with your own voice or an actor's voice:
1. Place a clean 10-30 second audio clip of the target voice in this folder:
   `Y:\Ultron\custom_voice\voice_sample.wav` (or `.mp3`)
2. Voice cloning models (like Coqui XTTS-v2 or ElevenLabs Voice Clone) can use this sample to replicate the vocal timbre and cadence.
