# SATYA — Technical Design Specification

## सत्य | Synthetic Audio & Video Authenticity

> _"Where Truth Speaks Every Language"_

**Team:** Imperials
**Member:** Sanjay Ravichandran
**Event:** AWS AI for Bharat Hackathon 2026
**Document Version:** 1.0 — February 10, 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Components](#2-architecture-components)
3. [Content Ingestion Pipeline](#3-content-ingestion-pipeline)
4. [Language Detection Engine](#4-language-detection-engine)
5. [AI Analysis Modules](#5-ai-analysis-modules)
6. [SATYA Scoring Engine](#6-satya-scoring-engine)
7. [Reporting & Translation Engine](#7-reporting--translation-engine)
8. [API Design](#8-api-design)
9. [Database Schema](#9-database-schema)
10. [Infrastructure (AWS)](#10-infrastructure-aws)
11. [Security Design](#11-security-design)
12. [Performance Benchmarks](#12-performance-benchmarks)
13. [Testing Strategy](#13-testing-strategy)
14. [Deployment Pipeline](#14-deployment-pipeline)
15. [Monitoring & Observability](#15-monitoring--observability)
16. [Future Enhancements](#16-future-enhancements)

---

## 1. System Overview

### 1.1 Objectives

SATYA is an AI-powered content authenticity platform that:

- Accepts content URLs from YouTube, Instagram, ShareChat, and X
- Performs multi-modal forensic analysis (video, audio, text)
- Produces a trust score (0–100) with explainable evidence
- Delivers results in any of 11 Indian languages
- Exposes a public dashboard tracking AI-generated content trends across India

### 1.2 Core Design Principles

| Principle          | Description                                                                             |
| ------------------ | --------------------------------------------------------------------------------------- |
| **Multi-Modal**    | Never rely on a single signal; fuse video, audio, and text forensics                    |
| **Multi-Lingual**  | Every component — detection, scoring, reporting, UI — works in 11 Indian languages      |
| **Multi-Platform** | Uniform ingestion layer abstracts away platform-specific APIs                           |
| **Explainable**    | Every score is accompanied by human-readable evidence                                   |
| **Privacy-First**  | Analyze and discard; never store user-submitted media beyond 24 hours                   |
| **Scalable**       | Serverless-first architecture; scale from 10 to 1M analyses/day without re-architecture |
| **Open Models**    | All AI models are open-source; zero vendor lock-in on inference                         |

### 1.3 High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                   │
│  ┌────────────┐  ┌──────────────────┐  ┌────────────────┐                │
│  │  Web App   │  │ Browser Extension│  │ Telegram Bot   │                │
│  │  (React +  │  │ (Chrome MV3)     │  │ (Node.js)      │                │
│  │  i18next)  │  │                  │  │                │                │
│  └─────┬──────┘  └────────┬─────────┘  └───────┬────────┘                │
│        └──────────────────┼────────────────────┘                         │
│                           ▼                                               │
│              ┌──────────────────────┐                                     │
│              │  Amazon API Gateway  │  ← JWT Auth + Rate Limiting        │
│              └──────────┬───────────┘                                     │
│                         ▼                                                 │
├───────────────────────────────────────────────────────────────────────────┤
│                         SERVICE LAYER                                     │
│                                                                           │
│  ┌──────────────────────────────────────────────────────────────┐         │
│  │              SATYA API (Python FastAPI on ECS Fargate)       │         │
│  │                                                              │         │
│  │  ┌────────────┐  ┌─────────────┐  ┌───────────────────┐     │         │
│  │  │ Ingestion  │  │ Orchestrator│  │ Result Composer   │     │         │
│  │  │ Service    │  │ Service     │  │ Service           │     │         │
│  │  └─────┬──────┘  └──────┬──────┘  └────────┬──────────┘     │         │
│  │        │                │                   │                │         │
│  └────────┼────────────────┼───────────────────┼────────────────┘         │
│           ▼                ▼                   ▼                          │
│  ┌────────────┐  ┌─────────────────────────────────────────┐             │
│  │ Amazon SQS │  │        AI ANALYSIS WORKERS              │             │
│  │ (Job Queue)│  │  (ECS Fargate / Lambda)                 │             │
│  └────────────┘  │                                         │             │
│                  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │             │
│                  │  │ Video    │ │ Audio    │ │ Text     │ │             │
│                  │  │ Forensic │ │ Forensic │ │ Analysis │ │             │
│                  │  │ Worker   │ │ Worker   │ │ Worker   │ │             │
│                  │  └──────────┘ └──────────┘ └──────────┘ │             │
│                  └─────────────────────────────────────────┘             │
│                                                                           │
├───────────────────────────────────────────────────────────────────────────┤
│                         DATA LAYER                                        │
│                                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐       │
│  │ Amazon S3  │  │ DynamoDB   │  │ CloudFront │  │ Amazon       │       │
│  │ (Media +   │  │ (Results + │  │ (Dashboard │  │ Translate    │       │
│  │  Reports)  │  │  Trending) │  │  CDN)      │  │ (i18n)       │       │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────┘       │
│                                                                           │
│  ┌────────────┐  ┌────────────┐                                          │
│  │ Amazon     │  │ Amazon     │                                          │
│  │ Bedrock    │  │ Rekognition│                                          │
│  │ (Explain-  │  │ (Suppl.   │                                          │
│  │  ability)  │  │  Face)     │                                          │
│  └────────────┘  └────────────┘                                          │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Architecture Components

### 2.1 Component Inventory

| Component                 | Runtime            | Language           | Responsibility                                        |
| ------------------------- | ------------------ | ------------------ | ----------------------------------------------------- |
| **Web Dashboard**         | CloudFront + S3    | TypeScript (React) | User interface for URL submission, results, dashboard |
| **Browser Extension**     | Chrome MV3         | TypeScript         | Right-click verification on any page                  |
| **Telegram Bot**          | ECS Fargate        | Node.js            | Chat-based verification interface                     |
| **API Gateway**           | Amazon API Gateway | —                  | Auth, throttling, routing                             |
| **SATYA API**             | ECS Fargate        | Python (FastAPI)   | Core orchestration, ingestion, result composition     |
| **Video Forensic Worker** | ECS Fargate (GPU)  | Python             | Deepfake detection, temporal analysis                 |
| **Audio Forensic Worker** | ECS Fargate        | Python             | Voice clone detection, spectral analysis              |
| **Text Analysis Worker**  | AWS Lambda         | Python             | LLM-text detection, bot detection                     |
| **Job Queue**             | Amazon SQS         | —                  | Async task distribution                               |
| **Media Storage**         | Amazon S3          | —                  | Temporary video/audio/frame storage                   |
| **Results Database**      | Amazon DynamoDB    | —                  | Analysis results, trending data                       |
| **Translation Service**   | Amazon Translate   | —                  | Report and UI translation                             |
| **Explainability Engine** | Amazon Bedrock     | —                  | Natural-language forensic explanations                |
| **Face Analysis**         | Amazon Rekognition | —                  | Supplementary facial forensic signals                 |

### 2.2 Inter-Component Communication

| From                    | To                | Protocol          | Pattern |
| ----------------------- | ----------------- | ----------------- | ------- |
| Client → API Gateway    | HTTPS             | Request-Response  |
| API Gateway → SATYA API | HTTP (internal)   | Request-Response  |
| SATYA API → SQS         | AWS SDK           | Async (enqueue)   |
| SQS → Workers           | AWS SDK           | Async (dequeue)   |
| Workers → S3            | AWS SDK           | Object put/get    |
| Workers → DynamoDB      | AWS SDK           | Write results     |
| SATYA API → DynamoDB    | AWS SDK           | Read results      |
| SATYA API → Bedrock     | AWS SDK           | Request-Response  |
| Dashboard → API Gateway | HTTPS + WebSocket | Real-time updates |

---

## 3. Content Ingestion Pipeline

### 3.1 Platform Connectors

Each supported platform has a dedicated connector module implementing a common `PlatformConnector` interface:

```
interface PlatformConnector:
    validate_url(url: str) -> bool
    extract_metadata(url: str) -> ContentMetadata
    download_video(url: str, output_path: str) -> VideoFile
    extract_audio(video: VideoFile) -> AudioFile
    extract_thumbnails(video: VideoFile) -> List[Image]
    get_text_content(url: str) -> TextContent  # title, desc, comments
```

#### YouTube Connector

| Attribute           | Detail                                                                   |
| ------------------- | ------------------------------------------------------------------------ |
| API                 | YouTube Data API v3                                                      |
| Authentication      | API Key (read-only; no OAuth needed for public videos)                   |
| Video Download      | `yt-dlp` library (open-source)                                           |
| Quota               | 10,000 units/day (1 video metadata = 1 unit; search = 100 units)         |
| Rate Limit Strategy | Token bucket: 50 requests/minute with exponential backoff                |
| Supported Content   | Public videos, Shorts, comments (first 100)                              |
| Metadata Extracted  | Title, description, channel info, publish date, view count, comment text |

#### Instagram Connector

| Attribute           | Detail                                               |
| ------------------- | ---------------------------------------------------- |
| API                 | Instagram Graph API + fallback web scraping          |
| Authentication      | OAuth 2.0 (App-level token for public content)       |
| Video Download      | `instaloader` library (open-source)                  |
| Rate Limit          | 200 calls/hour per user token                        |
| Rate Limit Strategy | Request queue with 18s spacing; user-upload fallback |
| Supported Content   | Reels, video posts                                   |
| Metadata Extracted  | Caption, hashtags, like count, comment text          |

#### ShareChat Connector

| Attribute           | Detail                                                     |
| ------------------- | ---------------------------------------------------------- |
| API                 | Web scraping (no public API)                               |
| Video Download      | HTTP download from CDN URLs extracted via headless browser |
| Rate Limit Strategy | 30 requests/minute; rotating user agents                   |
| Supported Content   | Short videos, image posts                                  |
| Metadata Extracted  | Title, description, share count, language tag              |

#### X (Twitter) Connector

| Attribute          | Detail                                                |
| ------------------ | ----------------------------------------------------- |
| API                | X API v2 (Basic tier)                                 |
| Authentication     | Bearer token                                          |
| Video Download     | Extract video URL from API response → HTTP download   |
| Rate Limit         | 10,000 tweets/month read (Basic); 100 requests/15 min |
| Supported Content  | Video tweets, image tweets, quote tweets              |
| Metadata Extracted | Tweet text, media URLs, engagement counts, reply text |

### 3.2 Media Processing Pipeline

```
URL Input
    │
    ▼
┌──────────────────┐
│  URL Validator &  │  ← Detect platform, validate format
│  Platform Router  │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Metadata        │  ← API call to platform for title, description,
│  Extractor       │     channel info, comments
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Video Downloader│  ← Download to S3 temp bucket
│  (yt-dlp / etc.) │     Max resolution: 720p (sufficient for forensics)
└────────┬─────────┘     Max duration: 10 minutes (MVP constraint)
         ▼
┌──────────────────┐
│  FFmpeg Pipeline │
│  ├─ Extract audio│  → WAV 16kHz mono → S3
│  ├─ Extract frames│ → JPEG at 2fps → S3
│  └─ Extract thumb │ → Original thumbnail → S3
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Language         │  ← Detect language from audio + text
│  Detection       │
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Job Dispatcher  │  ← Create 3 SQS messages:
│                  │     1. Video forensic job
│                  │     2. Audio forensic job
│                  │     3. Text analysis job
└──────────────────┘
```

### 3.3 S3 Bucket Structure

```
satya-media-{env}/
├── raw/
│   └── {analysis_id}/
│       ├── video.mp4
│       ├── audio.wav
│       └── metadata.json
├── frames/
│   └── {analysis_id}/
│       ├── frame_0001.jpg
│       ├── frame_0002.jpg
│       └── ...
├── reports/
│   └── {analysis_id}/
│       ├── report_en.pdf
│       ├── report_ta.pdf
│       └── report_hi.pdf
└── thumbnails/
    └── {analysis_id}/
        └── thumb.jpg
```

**Lifecycle Policy:** All objects in `raw/` and `frames/` are auto-deleted after 24 hours. Reports retained for 30 days.

---

## 4. Language Detection Engine

### 4.1 Detection Strategy

A two-stage detection approach:

**Stage 1 — Text-Based Detection**

- Input: Video title, description, comments from platform API
- Model: `fastText` pre-trained language identification model (`lid.176.bin`)
- Output: Detected language + confidence score
- Accuracy: > 95% for all 11 supported Indian languages
- Latency: < 10ms

**Stage 2 — Audio-Based Detection (Fallback)**

- Input: First 30 seconds of audio
- Model: OpenAI Whisper (language detection mode)
- Output: Detected spoken language + confidence score
- Triggered when: Text-based detection confidence < 70%, or no text available
- Latency: < 2 seconds

### 4.2 Code-Mixed Content Handling

| Scenario                               | Strategy                                                               |
| -------------------------------------- | ---------------------------------------------------------------------- |
| Hinglish (Hindi + English)             | Primary language = Hindi; English model also applied for text analysis |
| Tanglish (Tamil + English)             | Primary language = Tamil; English fallback for code-mixed phrases      |
| Multiple speakers, different languages | Audio segmented per speaker; each segment analyzed independently       |
| Title in English, audio in Tamil       | Both languages flagged; analysis runs for both                         |

### 4.3 Language Routing

Once detected, the language code is attached to the analysis job and routes to:

- Appropriate Whisper model variant for audio transcription
- Language-specific text perplexity model
- AWS Translate target language for report generation
- i18next locale key for UI rendering

---

## 5. AI Analysis Modules

### 5.1 Video Forensics Module

#### 5.1.1 Architecture

```
Input: Video frames (JPEG, 2fps from FFmpeg)
         │
         ▼
┌─────────────────────┐
│  Face Detection      │  ← YOLO-Face or MediaPipe
│  & Extraction       │     Extract face regions from each frame
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Deepfake Classifier│  ← Custom EfficientNet-B0 (ONNX)
│  Per-Face Score     │     Trained on FaceForensics++, Celeb-DF, DFDC
└─────────┬───────────┘     Output: P(fake) per face per frame
          ▼
┌─────────────────────┐
│  Temporal Analysis  │  ← Frame-to-frame consistency check
│                     │     • Face landmark jitter (68-point model)
│                     │     • Background flicker detection
│                     │     • Unnatural blink patterns
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  GAN / Diffusion    │  ← Frequency domain analysis (DCT)
│  Fingerprint Scanner│     Detect checkerboard artifacts (GAN)
│                     │     Detect spectral decay patterns (Diffusion)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Metadata Forensics │  ← Check EXIF data, encoding signatures
│                     │     AI-generated videos lack camera metadata
│                     │     Specific encoder fingerprints (Runway, Sora)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Video Score        │  ← Weighted aggregation of all signals
│  Aggregator         │     Output: video_authenticity_score (0–100)
│                     │     + per-signal breakdown
└─────────────────────┘
```

#### 5.1.2 Model Specifications

| Model               | Architecture         | Format | Size  | Input                 | Output                      |
| ------------------- | -------------------- | ------ | ----- | --------------------- | --------------------------- |
| Face Detector       | YOLOv8-nano-face     | ONNX   | 6 MB  | 640×640 RGB           | Bounding boxes + confidence |
| Deepfake Classifier | EfficientNet-B0      | ONNX   | 20 MB | 224×224 RGB face crop | P(fake) ∈ [0, 1]            |
| Landmark Detector   | MediaPipe Face Mesh  | TFLite | 2 MB  | Face crop             | 468 3D landmarks            |
| GAN Fingerprint     | Custom CNN (3-layer) | ONNX   | 5 MB  | 256×256 DCT spectrum  | P(GAN) ∈ [0, 1]             |

#### 5.1.3 Scoring Formula

```
video_score = 100 - (
    w_deepfake × avg(deepfake_scores)     +    # weight: 0.40
    w_temporal × temporal_anomaly_score    +    # weight: 0.25
    w_gan      × gan_fingerprint_score    +    # weight: 0.20
    w_metadata × metadata_anomaly_score        # weight: 0.15
) × 100

Where each component score ∈ [0, 1]
```

#### 5.1.4 Performance Targets

| Metric                               | Target                 |
| ------------------------------------ | ---------------------- |
| Frames processed per second          | 4 fps (on g4dn.xlarge) |
| 30-second video (60 frames at 2fps)  | < 15 seconds total     |
| Memory per analysis                  | < 2 GB                 |
| Accuracy (FaceForensics++ benchmark) | > 85% AUC              |
| False positive rate                  | < 12%                  |

### 5.2 Audio Forensics Module

#### 5.2.1 Architecture

```
Input: Audio waveform (16kHz WAV)
         │
         ▼
┌─────────────────────┐
│  Speech-to-Text     │  ← OpenAI Whisper (medium, multilingual)
│  Transcription      │     Outputs: transcript + timestamps + language
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Spectral Analysis  │  ← Librosa: compute Mel spectrogram, MFCCs
│                     │     Extract spectral features for clone detection
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Voice Clone        │  ← Custom classifier (ONNX)
│  Detector           │     Trained on ASVspoof 2024 dataset
│                     │     Features: MFCC deltas, spectral flux,
│                     │     zero-crossing rate, harmonic-to-noise ratio
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Prosody Analyzer   │  ← Check for unnatural patterns:
│                     │     • Flat pitch contour
│                     │     • Uniform speaking rate
│                     │     • Missing micro-pauses
│                     │     • Unnatural breath patterns
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Lip-Sync Checker   │  ← Compare audio timing with video lip movement
│  (Cross-Modal)      │     Deviation > 200ms = strong fake signal
│                     │     Uses SyncNet-style model
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Audio Score        │  ← Weighted aggregation
│  Aggregator         │     Output: audio_authenticity_score (0–100)
└─────────────────────┘
```

#### 5.2.2 Model Specifications

| Model                | Architecture     | Format         | Size   | Purpose                     |
| -------------------- | ---------------- | -------------- | ------ | --------------------------- |
| Whisper Medium       | Transformer      | PyTorch → ONNX | 1.5 GB | Transcription + language ID |
| Voice Clone Detector | LCNN (Light CNN) | ONNX           | 15 MB  | Synthetic voice detection   |
| Prosody Analyzer     | Rule-based + SVM | scikit-learn   | 2 MB   | Naturalness scoring         |
| Lip-Sync Model       | SyncNet          | ONNX           | 25 MB  | Audio-visual sync check     |

#### 5.2.3 Language-Specific Considerations

| Language Group                                | Challenge                       | Approach                                   |
| --------------------------------------------- | ------------------------------- | ------------------------------------------ |
| Hindi, Marathi (Devanagari)                   | Whisper well-supported          | Default Whisper multilingual               |
| Tamil, Telugu, Kannada, Malayalam (Dravidian) | Whisper accuracy ~80%           | Fine-tuned on IndicVoices dataset          |
| Bengali, Odia (Eastern Indo-Aryan)            | Moderate Whisper accuracy       | Fine-tuned on CommonVoice + IndicTTS       |
| Gujarati, Punjabi                             | Lower Whisper accuracy          | Use Indic Whisper variants where available |
| Code-mixed (Hinglish, Tanglish)               | Language switching mid-sentence | Whisper handles; custom post-processing    |

#### 5.2.4 Scoring Formula

```
audio_score = 100 - (
    w_clone   × voice_clone_score       +    # weight: 0.35
    w_prosody × prosody_anomaly_score   +    # weight: 0.25
    w_sync    × lip_sync_deviation      +    # weight: 0.25
    w_spectral× spectral_anomaly_score       # weight: 0.15
) × 100
```

### 5.3 Text Analysis Module

#### 5.3.1 Architecture

```
Input: Title + Description + Comments (text)
         │
         ▼
┌─────────────────────┐
│  Language Detection  │  ← fastText (already done in pipeline)
│  & Tokenization     │     Language-appropriate tokenizer
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  LLM-Text Detector  │  ← Perplexity-based analysis
│                     │     Low perplexity + low burstiness = LLM-generated
│                     │     Models: GPT-2 (English), IndicBERT (Indian langs)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Bot Comment        │  ← Pattern analysis on comments:
│  Detector           │     • Repetitive phrasing across comments
│                     │     • Posting time clustering
│                     │     • Account age / activity patterns
│                     │     • Semantic similarity scoring
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Coordinated        │  ← Network analysis:
│  Behavior Detector  │     • Multiple accounts posting identical text
│                     │     • Engagement spike without organic pattern
│                     │     • Cross-platform URL sharing patterns
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Text Score         │  ← Weighted aggregation
│  Aggregator         │     Output: text_authenticity_score (0–100)
└─────────────────────┘
```

#### 5.3.2 Perplexity Calculation

For each supported language, a reference language model is used:

| Language    | Reference Model        | Perplexity Threshold (LLM-generated) |
| ----------- | ---------------------- | ------------------------------------ |
| English     | GPT-2 (124M)           | < 30                                 |
| Hindi       | IndicBERT-Hindi        | < 40                                 |
| Tamil       | IndicBERT-Tamil        | < 45                                 |
| Telugu      | IndicBERT-Telugu       | < 45                                 |
| Bengali     | IndicBERT-Bengali      | < 45                                 |
| Other Indic | IndicBERT-multilingual | < 50                                 |

**Burstiness Score:** Measures variance in sentence-level perplexity. Human text is bursty (high variance); LLM text is uniform (low variance).

```
text_score = 100 - (
    w_perplexity × llm_detection_score   +    # weight: 0.40
    w_burstiness × burstiness_score      +    # weight: 0.25
    w_bot        × bot_comment_score     +    # weight: 0.20
    w_coordinated× coordinated_score          # weight: 0.15
) × 100
```

---

## 6. SATYA Scoring Engine

### 6.1 Score Fusion

The final SATYA Score combines all three modal scores:

```
satya_score = (
    W_video × video_score   +    # W_video = 0.50
    W_audio × audio_score   +    # W_audio = 0.30
    W_text  × text_score         # W_text  = 0.20
)
```

#### Adaptive Weighting

When a modality is unavailable (e.g., no audio in a silent video), weights are redistributed:

| Scenario                          | Video | Audio | Text |
| --------------------------------- | ----- | ----- | ---- |
| All available                     | 0.50  | 0.30  | 0.20 |
| No audio                          | 0.65  | 0.00  | 0.35 |
| No text (no description/comments) | 0.55  | 0.35  | 0.10 |
| Image only (no video/audio)       | 0.70  | 0.00  | 0.30 |

### 6.2 Confidence Calibration

Each score includes a **confidence level** based on:

| Factor                                      | Impact on Confidence              |
| ------------------------------------------- | --------------------------------- |
| Video duration (longer = more data)         | +10% per 30s, max +30%            |
| Number of faces detected                    | +5% per face, max +15%            |
| Audio clarity (SNR)                         | +10% if SNR > 20dB                |
| Text availability (title + desc + comments) | +5% per available field           |
| Language model coverage                     | +10% for well-supported languages |

```
confidence = base_confidence × Π(calibration_factors)

Categories:
  HIGH:   confidence > 0.80
  MEDIUM: confidence 0.50–0.80
  LOW:    confidence < 0.50
```

### 6.3 Verdict Categories

| Score Range | Verdict                             | Color  | Action                                 |
| ----------- | ----------------------------------- | ------ | -------------------------------------- |
| 0–49        | 🔴 High Risk — Likely AI-Generated  | Red    | Warn user; flag for dashboard          |
| 50–69       | 🟠 Suspicious — Partially Synthetic | Orange | Advise caution; suggest manual review  |
| 70–84       | 🟡 Uncertain — Inconclusive         | Yellow | Acknowledge uncertainty; show evidence |
| 85–100      | 🟢 Authentic — Likely Genuine       | Green  | Confirm authenticity                   |

### 6.4 Explainability Report Structure

Each analysis generates a structured explanation:

```json
{
  "satya_score": 34,
  "verdict": "HIGH_RISK",
  "confidence": "HIGH",
  "language": "ta",
  "summary": "இந்த வீடியோ AI-ஆல் உருவாக்கப்பட்டதாக அதிக வாய்ப்பு உள்ளது.",
  "findings": [
    {
      "module": "video_forensics",
      "signal": "deepfake_face",
      "severity": "HIGH",
      "detail": "Face boundary artifacts detected in 78% of frames",
      "evidence_frames": ["frame_0012.jpg", "frame_0045.jpg"]
    },
    {
      "module": "audio_forensics",
      "signal": "lip_sync_deviation",
      "severity": "HIGH",
      "detail": "Audio-lip sync deviation of 340ms detected",
      "evidence_timestamp": "00:12–00:18"
    },
    {
      "module": "audio_forensics",
      "signal": "voice_clone",
      "severity": "MEDIUM",
      "detail": "Spectral patterns consistent with TTS synthesis",
      "evidence_timestamp": "00:00–00:30"
    }
  ],
  "recommendations": [
    "Do not share this video",
    "Report to platform if impersonating a real person",
    "Use original source verification if available"
  ]
}
```

---

## 7. Reporting & Translation Engine

### 7.1 Report Generation Pipeline

```
Analysis Results (JSON)
         │
         ▼
┌─────────────────────┐
│  Template Engine    │  ← Jinja2 templates for web + PDF
│                     │     Separate templates per report section
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  AWS Translate      │  ← Translate findings to target language
│                     │     Source: English (all AI outputs are English)
│                     │     Target: User's detected/chosen language
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Amazon Bedrock     │  ← Generate natural-language explanation
│  (Claude / Llama)   │     Prompt: "Explain these forensic findings
│                     │     to a non-technical user in {language}"
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  PDF Generator      │  ← WeasyPrint / ReportLab
│  (with evidence     │     Include annotated frames
│   screenshots)      │     Include score breakdown charts
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Upload to S3       │  ← reports/{analysis_id}/report_{lang}.pdf
│                     │     Pre-signed URL for download (24h expiry)
└─────────────────────┘
```

### 7.2 Supported Output Formats

| Format        | Content                                   | Use Case                   |
| ------------- | ----------------------------------------- | -------------------------- |
| Web View      | Interactive HTML with expandable sections | Default for all users      |
| PDF           | Static report with evidence images        | Journalists, legal use     |
| JSON          | Raw structured data                       | API consumers, researchers |
| Short Summary | 280-character verdict                     | Telegram bot, sharing      |

---

## 8. API Design

### 8.1 REST API Endpoints

#### Analysis Endpoints

```
POST /api/v1/analyze
  Body: { "url": "https://youtube.com/watch?v=...", "language": "ta" }
  Response: { "analysis_id": "uuid", "status": "queued", "estimated_time": 8 }

GET /api/v1/analyze/{analysis_id}
  Response: { "status": "completed", "satya_score": 34, "report": {...} }

GET /api/v1/analyze/{analysis_id}/report?format=pdf&lang=ta
  Response: PDF binary / pre-signed S3 URL
```

#### Dashboard Endpoints

```
GET /api/v1/dashboard/trending
  Query: ?platform=youtube&language=ta&period=24h
  Response: { "trending_fakes": [...], "total_detected": 42 }

GET /api/v1/dashboard/heatmap
  Query: ?period=7d
  Response: { "regions": [{"state": "Tamil Nadu", "count": 156, ...}] }

GET /api/v1/dashboard/stats
  Response: { "total_analyses": 12345, "fakes_detected": 4567, ... }
```

#### Health & Meta

```
GET /api/v1/health
  Response: { "status": "ok", "version": "1.0.0", "uptime": "48h" }

GET /api/v1/platforms
  Response: { "supported": ["youtube", "instagram", "sharechat", "x"] }

GET /api/v1/languages
  Response: { "supported": ["en", "hi", "ta", "te", "bn", ...] }
```

### 8.2 WebSocket API

```
WS /ws/v1/analyze/{analysis_id}

Messages (server → client):
  { "event": "progress", "stage": "downloading", "percent": 20 }
  { "event": "progress", "stage": "video_analysis", "percent": 50 }
  { "event": "progress", "stage": "audio_analysis", "percent": 70 }
  { "event": "progress", "stage": "scoring", "percent": 90 }
  { "event": "complete", "satya_score": 34, "report_url": "..." }

Messages (server → dashboard clients):
  { "event": "new_fake_detected", "platform": "youtube", "score": 23, ... }
```

### 8.3 Authentication & Rate Limiting

| Tier           | Auth               | Rate Limit                | Features                           |
| -------------- | ------------------ | ------------------------- | ---------------------------------- |
| **Anonymous**  | None               | 5 analyses/day (IP-based) | Basic analysis, web view report    |
| **Free**       | JWT (email signup) | 20 analyses/day           | PDF reports, history               |
| **Pro**        | JWT + API key      | 200 analyses/day          | Bulk API, webhook callbacks        |
| **Enterprise** | JWT + API key      | Unlimited                 | SLA, priority queue, custom models |

### 8.4 Error Handling

```json
{
  "error": {
    "code": "UNSUPPORTED_PLATFORM",
    "message": "The URL provided is from an unsupported platform",
    "supported_platforms": [
      "youtube.com",
      "instagram.com",
      "sharechat.in",
      "x.com"
    ],
    "request_id": "req_abc123"
  }
}
```

| HTTP Code | Error Code           | Description                                |
| --------- | -------------------- | ------------------------------------------ |
| 400       | INVALID_URL          | URL format is invalid                      |
| 400       | UNSUPPORTED_PLATFORM | Platform not supported                     |
| 400       | VIDEO_TOO_LONG       | Video exceeds 10-minute limit (MVP)        |
| 403       | RATE_LIMIT_EXCEEDED  | Daily analysis quota reached               |
| 404       | ANALYSIS_NOT_FOUND   | Analysis ID does not exist                 |
| 410       | CONTENT_UNAVAILABLE  | Source video has been deleted/made private |
| 500       | ANALYSIS_FAILED      | Internal processing error                  |
| 503       | SERVICE_OVERLOADED   | Queue is full; retry later                 |

---

## 9. Database Schema

### 9.1 DynamoDB Tables

#### Table: `satya-analyses`

| Attribute            | Type              | Key      | Description                                    |
| -------------------- | ----------------- | -------- | ---------------------------------------------- |
| `analysis_id`        | String            | PK       | UUID v4                                        |
| `created_at`         | String (ISO 8601) | SK       | Timestamp                                      |
| `user_id`            | String            | GSI-1 PK | User who requested (or "anonymous")            |
| `platform`           | String            | GSI-2 PK | youtube / instagram / sharechat / x            |
| `content_url`        | String            | —        | Original URL                                   |
| `language`           | String            | —        | Detected language code                         |
| `status`             | String            | —        | queued / processing / completed / failed       |
| `satya_score`        | Number            | —        | 0–100                                          |
| `video_score`        | Number            | —        | 0–100                                          |
| `audio_score`        | Number            | —        | 0–100                                          |
| `text_score`         | Number            | —        | 0–100                                          |
| `confidence`         | String            | —        | HIGH / MEDIUM / LOW                            |
| `verdict`            | String            | —        | HIGH_RISK / SUSPICIOUS / UNCERTAIN / AUTHENTIC |
| `findings`           | Map               | —        | Detailed findings JSON                         |
| `report_urls`        | Map               | —        | { "en": "s3://...", "ta": "s3://...", ... }    |
| `processing_time_ms` | Number            | —        | Total processing duration                      |
| `ttl`                | Number            | —        | Auto-expire after 90 days                      |

**GSI-1:** `user_id` (PK) + `created_at` (SK) — Query user history
**GSI-2:** `platform` (PK) + `created_at` (SK) — Query by platform

#### Table: `satya-trending`

| Attribute             | Type                | Key    | Description                                 |
| --------------------- | ------------------- | ------ | ------------------------------------------- |
| `date`                | String (YYYY-MM-DD) | PK     | Date of detection                           |
| `platform#content_id` | String              | SK     | Platform + unique content ID                |
| `satya_score`         | Number              | —      | SATYA score                                 |
| `content_url`         | String              | —      | Original URL                                |
| `language`            | String              | —      | Content language                            |
| `platform`            | String              | GSI PK | Platform name                               |
| `estimated_views`     | Number              | —      | View count at detection time                |
| `detected_at`         | String (ISO 8601)   | —      | When SATYA first flagged this               |
| `category`            | String              | —      | politics / entertainment / finance / health |
| `region`              | String              | —      | Indian state if determinable                |
| `ttl`                 | Number              | —      | Auto-expire after 180 days                  |

#### Table: `satya-users`

| Attribute            | Type   | Key    | Description                         |
| -------------------- | ------ | ------ | ----------------------------------- |
| `user_id`            | String | PK     | UUID v4                             |
| `email`              | String | GSI PK | User email (unique)                 |
| `tier`               | String | —      | anonymous / free / pro / enterprise |
| `preferred_language` | String | —      | Default report language             |
| `analyses_today`     | Number | —      | Counter for rate limiting           |
| `created_at`         | String | —      | Registration timestamp              |

### 9.2 Capacity Planning

| Table            | Read Capacity | Write Capacity | Mode            |
| ---------------- | ------------- | -------------- | --------------- |
| `satya-analyses` | On-Demand     | On-Demand      | PAY_PER_REQUEST |
| `satya-trending` | On-Demand     | On-Demand      | PAY_PER_REQUEST |
| `satya-users`    | On-Demand     | On-Demand      | PAY_PER_REQUEST |

Estimated cost at 10K analyses/day: ~$5/month (DynamoDB on-demand).

---

## 10. Infrastructure (AWS)

### 10.1 Compute

| Service                    | Instance / Config       | Purpose                                  | Scaling                       |
| -------------------------- | ----------------------- | ---------------------------------------- | ----------------------------- |
| ECS Fargate (API)          | 2 vCPU, 4 GB RAM        | SATYA API server                         | 2–10 tasks (CPU-based)        |
| ECS Fargate (Video Worker) | 4 vCPU, 8 GB RAM, GPU\* | Video forensic analysis                  | 1–5 tasks (queue depth)       |
| ECS Fargate (Audio Worker) | 2 vCPU, 4 GB RAM        | Audio forensic analysis                  | 1–5 tasks (queue depth)       |
| AWS Lambda                 | 1 GB RAM, 5 min timeout | Text analysis, report gen, notifications | Automatic (0–1000 concurrent) |

\*Note: For hackathon demo, GPU analysis runs on a single EC2 `g4dn.xlarge` spot instance ($0.16/hr). Production would use ECS with GPU task definitions.

### 10.2 Storage

| Service                | Configuration                                  | Purpose                 | Cost Estimate |
| ---------------------- | ---------------------------------------------- | ----------------------- | ------------- |
| S3 Standard            | Lifecycle: 24h delete for raw, 30d for reports | Media + reports         | ~$2/month     |
| S3 Intelligent-Tiering | For trending content archives                  | Long-term trending data | ~$1/month     |

### 10.3 Networking

```
Internet
    │
    ▼
┌──────────────┐
│ CloudFront   │ ← Dashboard CDN (global edge, <50ms latency in India)
│ Distribution │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ API Gateway  │ ← REST + WebSocket APIs
│              │    Throttling: 1000 req/sec burst, 500 steady
│              │    WAF: Rate limiting, SQL injection protection
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ VPC          │
│ ┌──────────┐ │
│ │ Public   │ │ ← ALB for ECS services
│ │ Subnet   │ │
│ └────┬─────┘ │
│      │       │
│ ┌────▼─────┐ │
│ │ Private  │ │ ← ECS tasks, Lambda, DynamoDB endpoints
│ │ Subnet   │ │    No direct internet access (NAT Gateway for outbound)
│ └──────────┘ │
└──────────────┘
```

### 10.4 AWS Service Map

```
┌─────────────────────────────────────────────────────┐
│                  SATYA on AWS                        │
│                                                     │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │CloudFront│    │API GW   │    │Route 53 │         │
│  │(CDN)    │    │(API)    │    │(DNS)    │         │
│  └────┬────┘    └────┬────┘    └─────────┘         │
│       │              │                              │
│       └──────┬───────┘                              │
│              ▼                                      │
│  ┌──────────────────┐   ┌──────────────┐            │
│  │ ECS Fargate      │   │ Lambda       │            │
│  │ (API + Workers)  │   │ (Text + Gen) │            │
│  └────────┬─────────┘   └──────┬───────┘            │
│           │                    │                    │
│     ┌─────┼────────────────────┼─────┐              │
│     │     ▼                    ▼     │              │
│     │  ┌──────┐ ┌────────┐ ┌──────┐ │              │
│     │  │ SQS  │ │DynamoDB│ │  S3  │ │              │
│     │  │(Queue│ │(Data)  │ │(Store│ │              │
│     │  └──────┘ └────────┘ └──────┘ │              │
│     │                                │              │
│     │  ┌──────────┐ ┌────────────┐   │              │
│     │  │ Bedrock  │ │ Translate  │   │              │
│     │  │(Explain) │ │(i18n)      │   │              │
│     │  └──────────┘ └────────────┘   │              │
│     │                                │              │
│     │  ┌──────────┐ ┌────────────┐   │              │
│     │  │Rekognition│ │ CloudWatch │   │              │
│     │  │(Face)    │ │(Monitor)   │   │              │
│     │  └──────────┘ └────────────┘   │              │
│     └────────────────────────────────┘              │
└─────────────────────────────────────────────────────┘
```

### 10.5 Cost Estimate (Hackathon Demo)

| Service                | Usage                      | Cost                    |
| ---------------------- | -------------------------- | ----------------------- |
| ECS Fargate            | 2 tasks × 24h × 30 days    | $0 (Free Tier: 750 hrs) |
| EC2 Spot (g4dn.xlarge) | ~8 hrs/day × 30 days       | ~$38/month              |
| Lambda                 | 100K invocations           | $0 (Free Tier: 1M)      |
| S3                     | < 5 GB                     | $0 (Free Tier: 5 GB)    |
| DynamoDB               | < 25 GB, on-demand         | $0 (Free Tier: 25 GB)   |
| API Gateway            | < 1M calls                 | $0 (Free Tier: 1M)      |
| CloudFront             | < 50 GB transfer           | $0 (Free Tier: 50 GB)   |
| Translate              | < 2M characters            | $0 (Free Tier: 2M)      |
| Bedrock                | ~1000 calls (Claude Haiku) | ~$2/month               |
| SQS                    | < 1M messages              | $0 (Free Tier: 1M)      |
| **Total**              |                            | **~$40/month**          |

---

## 11. Security Design

### 11.1 Data Flow Security

| Data in Transit      | Protection                 |
| -------------------- | -------------------------- |
| Client → API Gateway | TLS 1.3 (enforced)         |
| API Gateway → ECS    | Internal HTTPS (ALB)       |
| ECS → S3             | VPC Endpoint (no internet) |
| ECS → DynamoDB       | VPC Endpoint (no internet) |

| Data at Rest         | Protection                                      |
| -------------------- | ----------------------------------------------- |
| S3 objects           | SSE-KMS (AWS managed key)                       |
| DynamoDB items       | Encryption enabled (default)                    |
| ECS task definitions | No secrets in env vars; use AWS Secrets Manager |

### 11.2 Authentication Flow

```
User → [Login/Signup] → API Gateway
    ← JWT token (RS256, 24h expiry)

User → [API Request + JWT] → API Gateway
    → Lambda Authorizer (validate JWT)
    → ECS (if valid)
    ← 401 Unauthorized (if invalid)
```

### 11.3 Privacy Safeguards

| Safeguard                  | Implementation                                  |
| -------------------------- | ----------------------------------------------- |
| No permanent video storage | S3 lifecycle: delete raw/\* after 24h           |
| No user tracking           | No analytics cookies; no tracking pixels        |
| Anonymized trending data   | Content IDs hashed; no user association         |
| Right to deletion          | DELETE /api/v1/user → purge all data within 24h |
| Data residency             | All data stored in `ap-south-1` (Mumbai)        |

---

## 12. Performance Benchmarks

### 12.1 End-to-End Latency Targets

| Content Type           | Duration    | Target Latency |
| ---------------------- | ----------- | -------------- |
| YouTube Short (15s)    | 15 seconds  | < 6 seconds    |
| YouTube Video (30s)    | 30 seconds  | < 10 seconds   |
| Instagram Reel (60s)   | 60 seconds  | < 15 seconds   |
| YouTube Video (5 min)  | 300 seconds | < 45 seconds   |
| YouTube Video (10 min) | 600 seconds | < 90 seconds   |

### 12.2 Throughput Targets

| Metric                  | Hackathon | Production |
| ----------------------- | --------- | ---------- |
| Concurrent analyses     | 50        | 1,000      |
| Analyses per day        | 10,000    | 1,000,000  |
| API requests per second | 100       | 5,000      |
| WebSocket connections   | 500       | 50,000     |

### 12.3 Module-Level Benchmarks

| Module                             | Input           | Latency | Memory |
| ---------------------------------- | --------------- | ------- | ------ |
| URL validation                     | URL string      | < 10ms  | N/A    |
| Video download (30s, 720p)         | URL             | < 3s    | 50 MB  |
| FFmpeg frame extraction (30s)      | Video file      | < 2s    | 100 MB |
| Face detection (per frame)         | 640×640 JPEG    | < 50ms  | 200 MB |
| Deepfake classification (per face) | 224×224 JPEG    | < 30ms  | 500 MB |
| Whisper transcription (30s audio)  | WAV 16kHz       | < 3s    | 1.5 GB |
| Voice clone detection (30s)        | Mel spectrogram | < 500ms | 200 MB |
| Text perplexity scoring            | Text block      | < 100ms | 500 MB |
| Score fusion                       | 3 scores        | < 5ms   | N/A    |
| Report generation (Bedrock)        | Findings JSON   | < 2s    | N/A    |
| PDF generation                     | HTML template   | < 3s    | 200 MB |

---

## 13. Testing Strategy

### 13.1 Unit Tests

| Module              | Framework      | Coverage Target | Key Test Cases                                              |
| ------------------- | -------------- | --------------- | ----------------------------------------------------------- |
| Platform connectors | pytest         | > 90%           | URL parsing, API mocking, error handling                    |
| Video forensics     | pytest         | > 85%           | Known deepfakes, known real videos, edge cases              |
| Audio forensics     | pytest         | > 85%           | Cloned voices, real voices, noisy audio                     |
| Text analysis       | pytest         | > 85%           | LLM text, human text, code-mixed text                       |
| Scoring engine      | pytest         | > 95%           | Weight calculation, edge cases (0, 100, missing modalities) |
| API endpoints       | pytest + httpx | > 90%           | Request validation, auth, error responses                   |

### 13.2 Integration Tests

| Test                  | Description                                                   | Frequency    |
| --------------------- | ------------------------------------------------------------- | ------------ |
| YouTube end-to-end    | Submit real YouTube URL → verify score returned               | Every deploy |
| Instagram end-to-end  | Submit real Instagram Reel → verify score returned            | Every deploy |
| Multi-language report | Analyze Hindi video → verify Tamil report generated           | Every deploy |
| WebSocket progress    | Connect WS → submit URL → verify all progress events received | Every deploy |
| S3 lifecycle          | Submit video → verify raw deleted after 24h                   | Weekly       |

### 13.3 Accuracy Benchmarks

| Dataset                   | Purpose                              | Size                    | Retest Frequency |
| ------------------------- | ------------------------------------ | ----------------------- | ---------------- |
| FaceForensics++           | Video deepfake detection accuracy    | 1,000 clips             | Monthly          |
| Celeb-DF v2               | Celebrity deepfake detection         | 590 clips               | Monthly          |
| ASVspoof 2024             | Voice clone detection accuracy       | 5,000 utterances        | Monthly          |
| Custom Indian Dataset     | Regional language detection accuracy | 500 clips (50/language) | Monthly          |
| GPT-generated text corpus | LLM text detection accuracy          | 2,000 samples           | Monthly          |

### 13.4 Load Tests

| Scenario                      | Tool          | Target                                |
| ----------------------------- | ------------- | ------------------------------------- |
| 100 concurrent analyses       | Locust        | All complete in < 2 minutes           |
| 1000 API requests/second      | k6            | p99 < 500ms                           |
| 500 WebSocket connections     | Artillery     | No dropped connections                |
| Queue backpressure (10K jobs) | Custom script | No message loss; graceful degradation |

---

## 14. Deployment Pipeline

### 14.1 CI/CD Architecture

```
GitHub Repository
    │
    ▼
┌──────────────────┐
│  GitHub Actions  │
│  ├─ lint         │  ← ruff (Python), eslint (TypeScript)
│  ├─ type-check   │  ← mypy (Python), tsc (TypeScript)
│  ├─ unit-test    │  ← pytest, vitest
│  ├─ build        │  ← Docker images (API, workers, dashboard)
│  ├─ push         │  ← ECR (container registry)
│  └─ deploy       │  ← ECS service update (rolling)
└──────────────────┘
```

### 14.2 Environments

| Environment | Purpose                   | Infra                 | Deploy Trigger                         |
| ----------- | ------------------------- | --------------------- | -------------------------------------- |
| `dev`       | Development testing       | Minimal (1 task each) | Push to `dev` branch                   |
| `staging`   | Pre-production validation | Mirror of prod        | Push to `staging` branch               |
| `prod`      | Live service              | Full scale            | Push to `main` branch (after approval) |

### 14.3 Deployment Strategy

- **API Service:** Rolling update (min 50% healthy, max 200%)
- **Workers:** Rolling update (drain SQS before stopping old tasks)
- **Dashboard:** S3 + CloudFront invalidation (blue-green via versioned prefixes)
- **Rollback:** Automatic if health check fails for 3 consecutive minutes

### 14.4 Infrastructure as Code

- **Tool:** AWS CDK (TypeScript)
- **Stacks:**
  - `SatyaNetworkStack` — VPC, subnets, security groups
  - `SatyaComputeStack` — ECS cluster, task definitions, Lambda functions
  - `SatyaDataStack` — S3 buckets, DynamoDB tables, SQS queues
  - `SatyaApiStack` — API Gateway, CloudFront distribution
  - `SatyaMonitoringStack` — CloudWatch dashboards, alarms, X-Ray

---

## 15. Monitoring & Observability

### 15.1 Metrics (CloudWatch)

| Metric                       | Alarm Threshold   | Action                         |
| ---------------------------- | ----------------- | ------------------------------ |
| `API_Latency_p95`            | > 500ms for 5 min | Alert on-call                  |
| `Analysis_Error_Rate`        | > 5% for 10 min   | Alert on-call                  |
| `SQS_Queue_Depth`            | > 1000 messages   | Scale up workers               |
| `ECS_CPU_Utilization`        | > 70% for 2 min   | Auto-scale up                  |
| `ECS_CPU_Utilization`        | < 20% for 10 min  | Auto-scale down                |
| `DynamoDB_ThrottledRequests` | > 0 for 5 min     | Switch to provisioned capacity |
| `S3_4xxErrors`               | > 10/min          | Investigate auth issues        |

### 15.2 Logging

| Component        | Log Destination                       | Retention |
| ---------------- | ------------------------------------- | --------- |
| API Server       | CloudWatch Logs `/satya/api`          | 30 days   |
| Video Worker     | CloudWatch Logs `/satya/video-worker` | 30 days   |
| Audio Worker     | CloudWatch Logs `/satya/audio-worker` | 30 days   |
| Lambda Functions | CloudWatch Logs `/aws/lambda/satya-*` | 14 days   |
| API Gateway      | CloudWatch Logs `/satya/api-gateway`  | 7 days    |

**Log Format:** Structured JSON with fields: `timestamp`, `level`, `service`, `analysis_id`, `message`, `duration_ms`, `error`.

### 15.3 Distributed Tracing

- **Service:** AWS X-Ray
- **Instrumentation:** All ECS services and Lambda functions instrumented with X-Ray SDK
- **Trace ID:** Propagated through SQS messages for end-to-end visibility
- **Sampling:** 5% in production, 100% in staging

### 15.4 Dashboard

A CloudWatch dashboard with panels for:

- Request volume (per platform, per language)
- Analysis latency distribution (p50, p90, p95, p99)
- Error rate by module
- Queue depth over time
- Active ECS tasks
- Cost tracker (daily spend)

---

## 16. Future Enhancements

### Phase 1 (Post-Hackathon, Month 1–3)

| Enhancement            | Description                                        |
| ---------------------- | -------------------------------------------------- |
| Browser Extension      | Chrome MV3 extension with right-click verification |
| Telegram Bot           | Full-featured bot with inline score display        |
| Creator Trust Passport | Voluntary creator verification + content signing   |
| Mobile PWA             | Progressive Web App for mobile-first experience    |

### Phase 2 (Month 4–6)

| Enhancement               | Description                                     |
| ------------------------- | ----------------------------------------------- |
| Real-Time Stream Analysis | WebRTC ingestion for live stream verification   |
| Platform Partnerships     | API integration with ShareChat, Josh, Moj       |
| Federated Detection       | Community-submitted model improvements          |
| Advanced GAN Detection    | Sora, Kling, Runway-specific fingerprint models |

### Phase 3 (Month 7–12)

| Enhancement          | Description                                          |
| -------------------- | ---------------------------------------------------- |
| Mobile Native Apps   | iOS + Android apps                                   |
| Enterprise Dashboard | Multi-tenant SaaS for platform moderators            |
| Research API         | Free API for academic researchers                    |
| SATYA Certification  | Industry-standard content authenticity certification |

---

_Document version: 1.0 — February 10, 2026_
