# SATYA — Product Requirements Document

## सत्य | Synthetic Audio & Video Authenticity

> _"Where Truth Speaks Every Language"_

**Team:** Imperials  
**Member:** Sanjay Ravichandran  
**Event:** AWS AI for Bharat Hackathon 2026

---

## 1. Executive Summary

SATYA (सत्य — Sanskrit for "Truth") is a multi-platform, multi-lingual AI content authenticity verification system. It addresses the rapidly growing crisis of AI-generated deepfake videos, synthetic audio, and LLM-generated text flooding Indian social media platforms — across languages that existing tools cannot serve.

Users can submit a link from YouTube, Instagram, ShareChat, or X, and receive an instant **SATYA Score (0–100)** indicating how likely the content is to be AI-generated, along with an explainable forensic report in any of 11 Indian languages.

---

## 2. Problem Statement

### 2.1 Market Context

| Metric                                                      | Value       |
| ----------------------------------------------------------- | ----------- |
| Indian internet users (2025)                                | 900M+       |
| Users consuming content in non-English languages            | ~70%        |
| YouTube users in India                                      | 467M        |
| Instagram users in India                                    | 230M        |
| ShareChat / Moj combined users                              | 340M        |
| Estimated scam losses from deepfakes in India (2025)        | ₹500+ crore |
| Accessible verification tools for regional language content | **0**       |

### 2.2 Real-World Incidents (2025–2026)

- **Election Deepfakes:** AI-generated videos of politicians making inflammatory statements went viral during 2025 state elections on WhatsApp, Instagram Reels, and YouTube Shorts, fueling communal tensions before any fact-checker could respond.
- **Celebrity Scam Ads:** Deepfake videos of Amitabh Bachchan, Virat Kohli, Rashmika Mandanna, and Sachin Tendulkar endorsing fake investment apps and crypto schemes caused thousands of Indians to lose money.
- **Creator Identity Theft:** Small Indian creators found their faces and voices cloned for scam ads and defamatory content they never made.
- **YouTube AI Slop:** Hundreds of "faceless" AI-generated channels pumped out fake news, fake history, and fake science content — all monetized, all undetected.
- **Trust Collapse:** 68% of Indian internet users reported they can no longer tell what is real online (Reuters Institute, 2025).

### 2.3 User Pain Points

| User                        | Pain Point                                                          |
| --------------------------- | ------------------------------------------------------------------- |
| Parents                     | Cannot verify if YouTube videos their children consume are real     |
| Regional language users     | Zero verification tools for Tamil, Telugu, Bengali, Kannada content |
| Journalists / Fact-checkers | Spend hours manually verifying viral content; no scalable tool      |
| Content creators            | Deepfakes using their identity damage reputation; no recourse       |
| Social media platforms      | Manual moderation cannot keep up at scale                           |

---

## 3. Target Users

### 3.1 Primary Users

#### P1 — Everyday Internet Users (100M+ potential)

- **Demographics:** Age 18–45, Tier 1–3 cities
- **Languages:** All 11 supported Indian languages
- **Platforms used:** YouTube, Instagram, ShareChat, X
- **Need:** Quick, intuitive verification — "Is this video real?"
- **Tech comfort:** Basic smartphone user; must require zero technical knowledge

#### P2 — Content Creators (50M+ in India)

- **Demographics:** Small to mid-size YouTubers, Instagram creators, regional influencers
- **Need:** Protect identity from deepfakes; build audience trust
- **Workflow:** Needs integration into existing content workflows

#### P3 — Journalists & Fact-Checkers (50K+)

- **Demographics:** Regional and national media professionals
- **Need:** Fast, reliable, bulk verification with forensic-grade reports
- **Workflow:** Must generate shareable evidence for articles

### 3.2 Secondary Users

#### S1 — Brands & Marketing Teams

- **Need:** Verify no deepfakes in campaigns; monitor brand reputation
- **Workflow:** API or dashboard-based bulk monitoring

#### S2 — Parents & Educators

- **Need:** Ensure children don't consume harmful AI-generated content
- **Workflow:** Simple URL-paste verification; possible browser extension

#### S3 — Platform Moderators (YouTube, ShareChat, Instagram)

- **Need:** API integration for automated pre-publish content screening
- **Workflow:** REST API with webhook callbacks

---

## 4. Functional Requirements

### 4.1 Core Features — MVP (Hackathon Scope)

#### FR-1: Multi-Platform Content Ingestion

| Field                   | Specification                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------- |
| **ID**                  | FR-1                                                                                               |
| **Priority**            | P0 — Must-have                                                                                     |
| **Input**               | URL from YouTube, Instagram Reels, ShareChat, or X                                                 |
| **Process**             | Download video, extract audio track, extract metadata, detect language                             |
| **Platforms**           | YouTube (via Data API v3), Instagram (via Graph API), ShareChat (via scraping/API), X (via API v2) |
| **Constraints**         | Respect platform rate limits; implement queue for async processing                                 |
| **Acceptance Criteria** | User pastes a valid URL → system acknowledges within 2s → analysis begins                          |

#### FR-2: Multi-Modal AI Detection Engine

| Field        | Specification  |
| ------------ | -------------- |
| **ID**       | FR-2           |
| **Priority** | P0 — Must-have |

**FR-2.1 — Video Forensics**

| Attribute       | Detail                                                                                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Models          | Custom CNN (ONNX Runtime) for deepfake detection                                                                                      |
| Input           | Video frames sampled at 2 fps                                                                                                         |
| Detections      | Face boundary artifacts, temporal inconsistency (frame-to-frame jitter), GAN / diffusion fingerprint patterns, lighting inconsistency |
| Output          | Per-frame anomaly scores → aggregated video authenticity score                                                                        |
| Accuracy Target | > 85% on benchmark datasets                                                                                                           |
| Performance     | < 500ms per frame on GPU instance                                                                                                     |

**FR-2.2 — Audio Forensics**

| Attribute       | Detail                                                                                                                     |
| --------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Models          | OpenAI Whisper (multilingual, open-source) + custom spectral classifier                                                    |
| Input           | Audio waveform (16 kHz WAV)                                                                                                |
| Detections      | Voice cloning signatures (spectral analysis), unnatural prosody, synthetic noise patterns, audio-visual lip-sync deviation |
| Languages       | All 11 Indian languages                                                                                                    |
| Accuracy Target | > 80% per language                                                                                                         |
| Performance     | < 2 seconds for 1-minute audio                                                                                             |

**FR-2.3 — Text Analysis**

| Attribute   | Detail                                                                                |
| ----------- | ------------------------------------------------------------------------------------- |
| Models      | Custom perplexity scorer + burstiness detector                                        |
| Input       | Video titles, descriptions, captions, comments                                        |
| Detections  | LLM-generated text patterns, bot comment signatures, coordinated inauthentic behavior |
| Languages   | All 11 Indian languages (separate models per language)                                |
| Performance | < 100ms per text block                                                                |

#### FR-3: SATYA Scoring System

| Field                   | Specification                                                                                  |
| ----------------------- | ---------------------------------------------------------------------------------------------- |
| **ID**                  | FR-3                                                                                           |
| **Priority**            | P0 — Must-have                                                                                 |
| **Score Range**         | 0–100                                                                                          |
| **Fusion Weights**      | Video: 50%, Audio: 30%, Text: 20%                                                              |
| **Categories**          | 🔴 0–49: High Risk (AI-generated) · 🟡 50–84: Uncertain (needs review) · 🟢 85–100: Authentic  |
| **Explainability**      | Each score accompanied by top contributing features and confidence intervals                   |
| **Acceptance Criteria** | Score is deterministic for same input; explainability text generated in user's chosen language |

#### FR-4: Multi-Language Report Generation

| Field                   | Specification                                                                                                        |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **ID**                  | FR-4                                                                                                                 |
| **Priority**            | P0 — Must-have                                                                                                       |
| **Report Includes**     | SATYA score with color-coded indicator, detailed findings, annotated video frames showing anomalies, recommendations |
| **Languages**           | All 11 supported Indian languages                                                                                    |
| **Formats**             | Web view + PDF download                                                                                              |
| **Translation**         | AWS Translate for UI and report text                                                                                 |
| **Acceptance Criteria** | Report loads in < 3 seconds; PDF generated in < 5 seconds; all text is in chosen language                            |

#### FR-5: Web Dashboard

| Field                   | Specification                                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **ID**                  | FR-5                                                                                                                             |
| **Priority**            | P0 — Must-have                                                                                                                   |
| **Features**            | Paste URL → instant analysis; analysis history; trending fakes feed; India Trust Heatmap (geographic distribution of AI content) |
| **UI Languages**        | Full interface in all 11 languages (i18next)                                                                                     |
| **Responsiveness**      | Mobile-first responsive design                                                                                                   |
| **Acceptance Criteria** | 3-click maximum from landing to SATYA score; dashboard loads in < 2s                                                             |

### 4.2 Extended Features — Post-MVP

#### FR-6: Browser Extension

| Field             | Specification                                                                               |
| ----------------- | ------------------------------------------------------------------------------------------- |
| **ID**            | FR-6                                                                                        |
| **Priority**      | P1 — Should-have                                                                            |
| **Functionality** | Right-click any video link → "Verify with SATYA"; inline score badge on YouTube / Instagram |
| **Platform**      | Chrome (Manifest V3)                                                                        |

#### FR-7: Telegram Bot

| Field             | Specification                                                                  |
| ----------------- | ------------------------------------------------------------------------------ |
| **ID**            | FR-7                                                                           |
| **Priority**      | P1 — Should-have                                                               |
| **Functionality** | Send video link → receive SATYA score + summary in chosen language             |
| **Why Telegram**  | Works when WhatsApp is restricted; open bot API; supports rich media responses |

#### FR-8: Bulk Analysis API

| Field             | Specification                             |
| ----------------- | ----------------------------------------- |
| **ID**            | FR-8                                      |
| **Priority**      | P2 — Nice-to-have                         |
| **Functionality** | Upload CSV of URLs → receive batch report |
| **Target Users**  | Fact-checkers, researchers                |

#### FR-9: Creator Trust Passport

| Field             | Specification                                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **ID**            | FR-9                                                                                                                         |
| **Priority**      | P2 — Nice-to-have                                                                                                            |
| **Functionality** | Verified creator registration (Aadhaar / DigiLocker KYC); cryptographic content signing; tamper detection for signed content |

---

## 5. Non-Functional Requirements

### NFR-1: Performance

| Metric                              | Target       |
| ----------------------------------- | ------------ |
| 30-second video analysis end-to-end | < 10 seconds |
| API response time (p95)             | < 200ms      |
| Dashboard initial load              | < 2 seconds  |
| Concurrent analyses supported       | 1,000        |

### NFR-2: Accuracy

| Metric                                              | Target |
| --------------------------------------------------- | ------ |
| Video deepfake detection accuracy                   | > 85%  |
| Audio voice-clone detection accuracy (per language) | > 80%  |
| Text LLM-generation detection accuracy              | > 80%  |
| Overall false positive rate                         | < 15%  |

### NFR-3: Scalability

| Metric                  | Target                   |
| ----------------------- | ------------------------ |
| Hackathon demo capacity | 10,000 analyses / day    |
| Post-launch target      | 1,000,000 analyses / day |
| Auto-scaling trigger    | CPU > 70% for 2 minutes  |

### NFR-4: Availability

| Metric               | Target        |
| -------------------- | ------------- |
| Uptime SLA           | 99.5%         |
| Recovery time (MTTR) | < 5 minutes   |
| Data durability (S3) | 99.999999999% |

### NFR-5: Security & Privacy

- No permanent storage of user-submitted videos (auto-delete after 24 hours)
- Encryption at rest (S3 SSE-KMS) and in transit (TLS 1.3)
- Compliance with India Digital Personal Data Protection Act, 2023
- No user tracking for what content they verify
- JWT-based authentication for API access

### NFR-6: Usability

- Zero learning curve for everyday users
- Maximum 3 clicks from landing page to SATYA score
- Mobile-responsive (works on ₹8,000 smartphones)
- Accessible (WCAG 2.1 AA compliance)

### NFR-7: Localization

- Full UI translation for all 11 Indian languages
- Culturally appropriate iconography and messaging
- Number and date formatting per locale
- Support for code-mixed content (Hinglish, Tanglish)

---

## 6. User Stories

### US-1: Verify a YouTube Video (Everyday User)

> **As a** parent in Tamil Nadu  
> **I want to** paste a YouTube URL and verify if the video is real  
> **So that** I can protect my child from AI-generated misinformation

**Acceptance Criteria:**

- [ ] Can paste YouTube URL in Tamil UI
- [ ] Gets SATYA score in < 10 seconds
- [ ] Report is displayed in Tamil
- [ ] Score is color-coded (🔴🟡🟢) and easy to understand

### US-2: Detect Identity Theft (Content Creator)

> **As a** regional YouTuber with 50K subscribers  
> **I want to** check if a video uses a deepfake of my face  
> **So that** I can take it down before it damages my reputation

**Acceptance Criteria:**

- [ ] Can submit suspected deepfake URL
- [ ] System identifies it as fake (if it is) with > 85% accuracy
- [ ] Provides forensic evidence usable for DMCA takedown request

### US-3: Batch Verify Viral Content (Journalist)

> **As a** fact-checker at a regional news outlet  
> **I want to** verify 10 viral videos before publishing my article  
> **So that** I don't inadvertently spread misinformation

**Acceptance Criteria:**

- [ ] Can submit multiple URLs for batch analysis
- [ ] Gets detailed forensic report for each
- [ ] Reports include annotated screenshots usable in articles
- [ ] Total turnaround < 5 minutes for 10 videos

### US-4: Integrate Moderation API (Platform Moderator)

> **As a** moderator at a regional social media platform  
> **I want to** integrate SATYA API into our upload pipeline  
> **So that** AI-generated content is auto-flagged before publishing

**Acceptance Criteria:**

- [ ] REST API with < 1 second response time for short videos
- [ ] Webhook support for async results
- [ ] 99.5% uptime
- [ ] Clear API documentation

### US-5: View Trending Fakes (Researcher)

> **As a** misinformation researcher  
> **I want to** see which AI-generated videos are trending in India right now  
> **So that** I can study spread patterns and publish findings

**Acceptance Criteria:**

- [ ] Public dashboard showing trending AI content by platform and region
- [ ] Geographic heatmap of AI content density
- [ ] Data exportable as CSV for research

---

## 7. Supported Platforms

| #   | Platform    | Integration Method | Content Types            |
| --- | ----------- | ------------------ | ------------------------ |
| 1   | YouTube     | Data API v3        | Videos, Shorts, comments |
| 2   | Instagram   | Graph API          | Reels, posts, stories    |
| 3   | ShareChat   | Web scraping + API | Short videos, images     |
| 4   | X (Twitter) | API v2             | Videos, images, posts    |
| 5   | Moj         | Future             | Short videos             |

---

## 8. Supported Languages

| #   | Language  | Script     | Video Analysis | Audio Analysis | Text Analysis | UI  |
| --- | --------- | ---------- | :------------: | :------------: | :-----------: | :-: |
| 1   | English   | Latin      |       ✅       |       ✅       |      ✅       | ✅  |
| 2   | Hindi     | Devanagari |       ✅       |       ✅       |      ✅       | ✅  |
| 3   | Tamil     | Tamil      |       ✅       |       ✅       |      ✅       | ✅  |
| 4   | Telugu    | Telugu     |       ✅       |       ✅       |      ✅       | ✅  |
| 5   | Bengali   | Bengali    |       ✅       |       ✅       |      ✅       | ✅  |
| 6   | Kannada   | Kannada    |       ✅       |       ✅       |      ✅       | ✅  |
| 7   | Malayalam | Malayalam  |       ✅       |       ✅       |      ✅       | ✅  |
| 8   | Marathi   | Devanagari |       ✅       |       ✅       |      ✅       | ✅  |
| 9   | Gujarati  | Gujarati   |       ✅       |       ✅       |      ✅       | ✅  |
| 10  | Punjabi   | Gurmukhi   |       ✅       |       ✅       |      ✅       | ✅  |
| 11  | Odia      | Odia       |       ✅       |       ✅       |      ✅       | ✅  |

---

## 9. Technical Constraints

| ID   | Constraint                               | Impact                       | Mitigation                                          |
| ---- | ---------------------------------------- | ---------------------------- | --------------------------------------------------- |
| TC-1 | YouTube Data API: 10,000 quota units/day | Limits daily analyses        | Request quota increase; implement caching           |
| TC-2 | Instagram Graph API: 200 calls/hour      | Rate-limited ingestion       | Queue management; user-uploaded fallback            |
| TC-3 | AWS Lambda: 10 GB package limit          | Model size constrained       | Use ONNX Runtime; quantize models                   |
| TC-4 | Low-resource languages (Odia, Punjabi)   | Lower detection accuracy     | Custom fine-tuning; community contribution pipeline |
| TC-5 | Cost: $0 for hackathon                   | Must use free-tier resources | Open-source models; AWS Free Tier; spot instances   |

---

## 10. AWS Services Used

| Service              | Purpose                                           |
| -------------------- | ------------------------------------------------- |
| Amazon ECS (Fargate) | API server and AI inference containers            |
| AWS Lambda           | Async tasks (report generation, notifications)    |
| Amazon S3            | Media upload, processed frames, report storage    |
| Amazon DynamoDB      | Analysis results, user data, trending fakes       |
| Amazon API Gateway   | REST API with throttling and auth                 |
| Amazon CloudFront    | Dashboard CDN                                     |
| Amazon Bedrock       | Explainability report generation (Claude / Llama) |
| Amazon Translate     | Multi-language report and UI translation          |
| Amazon Rekognition   | Supplementary face analysis                       |
| Amazon CloudWatch    | Logging, metrics, alarms                          |
| AWS X-Ray            | Distributed tracing                               |

---

## 11. Success Metrics

### Adoption

| Metric                         | Hackathon Target | 6-Month Target |
| ------------------------------ | ---------------- | -------------- |
| Total analyses                 | 1,000            | 1,000,000      |
| Returning users (2nd analysis) | 50%              | 40%            |
| Early access sign-ups          | 500              | 50,000         |

### Accuracy

| Metric                                               | Target |
| ---------------------------------------------------- | ------ |
| User-reported accuracy ("Was this verdict correct?") | > 80%  |
| Benchmark dataset accuracy                           | > 85%  |

### Performance

| Metric            | Target       |
| ----------------- | ------------ |
| p95 analysis time | < 10 seconds |
| API uptime        | > 99%        |

### Impact

| Metric                                 | Target |
| -------------------------------------- | ------ |
| Viral fakes detected during hackathon  | 100+   |
| Fact-checking orgs expressing interest | 2+     |

---

## 12. Risks & Mitigation

| ID  | Risk                                              | Severity  | Mitigation                                                                                   |
| --- | ------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------- |
| R-1 | Platform API restrictions / bans                  | 🔴 High   | Comply strictly with ToS; rate limiting; user-uploaded video fallback                        |
| R-2 | AI generation models evolve faster than detection | 🔴 High   | Modular model architecture; continuous retraining pipeline; community model updates          |
| R-3 | False positives damage trust in real creators     | 🟡 Medium | Conservative thresholds; "Uncertain" category; human appeal process                          |
| R-4 | Compute costs exceed budget at scale              | 🟡 Medium | Tiered analysis (quick scan free, deep forensic premium); spot instances; model quantization |
| R-5 | Regulatory changes (India IT Act amendments)      | 🟡 Medium | Legal review; privacy-by-design; compliance monitoring                                       |
| R-6 | Low accuracy for low-resource languages           | 🟡 Medium | Community data contribution; partner with language research institutes                       |

---

## 13. Out of Scope (Not in MVP)

- Real-time live stream analysis
- Native mobile apps (iOS / Android)
- Content creation or editing tools
- Social media scheduling or posting
- Deepfake generation capabilities
- Paid subscription billing system

---

## 14. Timeline (Hackathon Sprint)

| Week   | Deliverable                                             |
| ------ | ------------------------------------------------------- |
| Week 1 | Core AI models (video + audio) + YouTube integration    |
| Week 2 | Multi-platform ingestion + SATYA scoring engine         |
| Week 3 | Web dashboard + multi-language support + Telegram bot   |
| Week 4 | Testing, demo video, presentation, documentation polish |

---

## 15. Post-Hackathon Roadmap

| Phase                     | Timeline   | Goals                                                                    |
| ------------------------- | ---------- | ------------------------------------------------------------------------ |
| **Phase 1: Beta**         | Month 1–3  | Browser extension; Telegram bot; 100 early access users                  |
| **Phase 2: Partnerships** | Month 4–6  | API for ShareChat / regional platforms; 3 fact-checking org partnerships |
| **Phase 3: Scale**        | Month 7–12 | 1M analyses/month; premium tier; enterprise API partnerships             |

---

_Document version: 1.0 — February 10, 2026_
