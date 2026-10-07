# SafeTrack AI

### Autonomous Vision & Behaviour Understanding

**HackNEX 2026 | HNX26PSI07 | Computer Vision**

SafeTrack AI is a computer-vision-based safety monitoring system designed to detect, track, and understand human behaviour in video footage. The system goes beyond simple object detection by analysing tracked entities over time and identifying meaningful abnormal events.

The initial MVP focuses on detecting **prolonged presence inside a predefined restricted zone** and generating a timestamped event with supporting visual evidence.

---

## 1. Problem Statement

Traditional video surveillance systems can detect objects or record footage, but they often require continuous human monitoring to identify meaningful events.

The HNX26PSI07 problem focuses on building a system that can:

* Detect people and relevant objects
* Track entities across video frames
* Understand basic behaviour
* Distinguish normal and abnormal behaviour
* Identify meaningful events
* Provide the affected entity and event timing
* Produce evidence for abnormal behaviour

SafeTrack AI addresses this by combining object detection, multi-object tracking, spatial zone analysis, and temporal behaviour reasoning.

---

## 2. Objective

The objective of SafeTrack AI is to create a lightweight and explainable vision system that can transform raw video into meaningful safety events.

### MVP Objective

Detect when a tracked person:

1. Enters a predefined restricted zone
2. Remains inside the zone
3. Exceeds a configurable time threshold
4. Triggers an abnormal-behaviour event

The system then records:

* Person tracking ID
* Event type
* Start timestamp
* End timestamp
* Duration
* Configured threshold
* Reason for the alert
* Evidence frame or clip
* Confidence information where applicable

---

## 3. Proposed Solution

SafeTrack AI follows the pipeline:

```text
Video Input
     ↓
Frame Processing
     ↓
Person/Object Detection
     ↓
Multi-Object Tracking
     ↓
Restricted-Zone Analysis
     ↓
Temporal Behaviour Analysis
     ↓
Normal / Abnormal Classification
     ↓
Timestamped Event
     ↓
Evidence Generation
     ↓
Dashboard / Report
```

The system maintains a tracking identity for each detected person and uses their movement across frames to determine whether a meaningful event has occurred.

---

## 4. MVP Behaviour

### Restricted-Zone Prolonged Presence

A restricted area is defined as a polygonal region in the video.

When a tracked person enters the region:

```text
Person enters zone
       ↓
Start timer
       ↓
Person remains inside
       ↓
Threshold exceeded?
     ↙       ↘
   No         Yes
   ↓           ↓
Normal    Abnormal Event
              ↓
       Save timestamp
              ↓
       Save evidence
```

### Example Event

```text
Event ID: EVT-001
Person ID: 3
Event: Prolonged Restricted-Zone Presence
Entry Time: 00:01:12
Duration: 14.8 seconds
Threshold: 10 seconds
Status: ABNORMAL

Reason:
Person 3 remained inside the restricted zone for
14.8 seconds, exceeding the configured limit of 10 seconds.
```

---

## 5. Key Features

### Detection

* Detect people and relevant objects from video
* Record bounding boxes and confidence scores

### Tracking

* Assign tracking IDs to detected people
* Maintain identities across consecutive frames
* Handle temporary detection loss where possible

### Zone Analysis

* Configurable polygonal restricted zones
* Determine whether tracked entities enter or leave a zone
* Use the tracked person's position for zone evaluation

### Behaviour Analysis

* Monitor behaviour over time
* Measure duration inside restricted areas
* Distinguish normal and abnormal events

### Event Generation

* Generate meaningful events instead of frame-by-frame alerts
* Include entity ID and timestamp
* Prevent duplicate event generation

### Evidence

* Save relevant event frames
* Record structured event information
* Provide explainable reasons for abnormal-event flags

### Dashboard

* Upload/select video
* Run analysis
* View processed results
* View detected entities and tracking IDs
* View abnormal events and timestamps
* View supporting evidence

---

## 6. Technology Stack

| Component            | Technology            |
| -------------------- | --------------------- |
| Programming Language | Python                |
| Computer Vision      | OpenCV                |
| Object Detection     | YOLO-family detector  |
| Object Tracking      | Multi-object tracking |
| Configuration        | YAML                  |
| Event Output         | JSON                  |
| Dashboard            | Streamlit             |
| Version Control      | Git / GitHub          |

Specific models and implementations will be documented in `docs/resources.md`.

---

## 7. Project Structure

```text
SafeTrack-AI/
│
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── config.yaml
│
├── src/
│   ├── main.py
│   │
│   ├── detection/
│   │   └── detector.py
│   │
│   ├── tracking/
│   │   └── tracker.py
│   │
│   ├── zones/
│   │   └── zone_manager.py
│   │
│   ├── behaviour/
│   │   └── behaviour_analyzer.py
│   │
│   ├── evidence/
│   │   └── evidence_manager.py
│   │
│   └── utils/
│       ├── config.py
│       ├── video.py
│       └── logger.py
│
├── dashboard/
│   └── app.py
│
├── tests/
│
├── data/
│   ├── sample/
│   └── outputs/
│
├── demo/
│
└── docs/
    ├── architecture.md
    ├── data_pipeline.md
    ├── model.md
    ├── testing.md
    └── resources.md
```

---

## 8. Data Pipeline

The system processes video through the following stages:

### 1. Input Collection

A video file is provided as input.

### 2. Frame Processing

The video is divided into frames and processed sequentially.

### 3. Detection

The vision model identifies people and relevant objects.

### 4. Tracking

Detected entities are assigned tracking IDs and followed across frames.

### 5. Spatial Analysis

The system determines whether an entity is inside a configured restricted zone.

### 6. Temporal Analysis

The system maintains the entity's state and measures how long it remains in the zone.

### 7. Behaviour Classification

The system compares the observed behaviour against configured rules.

### 8. Event Generation

An abnormal event is generated when the behaviour exceeds the defined threshold.

### 9. Evidence Generation

Relevant frames, timestamps, tracking information, and event details are stored.

### 10. Output

Results are presented through structured JSON and the dashboard.

---

## 9. Configuration

Important parameters are stored in `config.yaml`.

Example:

```yaml
video:
  input_path: "data/sample/sample.mp4"

detection:
  confidence_threshold: 0.5

behaviour:
  restricted_zone_duration_seconds: 10

output:
  directory: "data/outputs"
```

Values can be modified without changing the core source code.

---

## 10. Installation

Clone the repository:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd SafeTrack-AI
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 11. Running the System

The main processing pipeline will be launched using:

```bash
python -m src.main
```

The dashboard will be launched using:

```bash
streamlit run dashboard/app.py
```

Exact commands may be updated as implementation progresses.

---

## 12. Sample Input

The MVP will use short workplace, laboratory, industrial, or simulated safety videos containing:

* Normal movement
* Restricted-zone entry
* Brief restricted-zone entry
* Prolonged restricted-zone presence
* Multiple people where possible

Large video datasets should not be committed directly to the Git repository.

---

## 13. Sample Output

A structured event will be generated in JSON format.

Example:

```json
{
  "event_id": "EVT-001",
  "event_type": "restricted_zone_prolonged_presence",
  "person_id": 3,
  "start_time": "00:01:12",
  "end_time": "00:01:27",
  "duration_seconds": 15.0,
  "threshold_seconds": 10.0,
  "status": "ABNORMAL",
  "reason": "Person remained inside the restricted zone beyond the configured threshold.",
  "evidence": "evidence/EVT-001.jpg"
}
```

---

## 14. Evidence & Explainability

SafeTrack AI is designed so that an abnormal event is not simply reported as:

```text
Anomaly detected.
```

Instead, the system provides an interpretable explanation:

```text
Person 3 remained inside the restricted zone for
15.0 seconds, exceeding the configured limit of 10 seconds.
```

Evidence can include:

* Event timestamp
* Tracking ID
* Bounding box
* Duration
* Zone information
* Detection confidence
* Evidence frame
* Optional event clip

---

## 15. Testing

The system will be evaluated using controlled test cases.

| Test Case                           | Expected Result                 |
| ----------------------------------- | ------------------------------- |
| Person stays outside zone           | Normal                          |
| Person briefly enters zone          | Normal                          |
| Person remains beyond threshold     | Abnormal event                  |
| Multiple people in scene            | Individual tracking             |
| Person exits after triggering event | Event closed                    |
| Temporary detection loss            | Tracking handled where possible |

Detailed testing results will be documented in `docs/testing.md`.

---

## 16. MVP vs Stretch Goals

### MVP

* Video input
* Person detection
* Multi-object tracking
* Restricted-zone definition
* Entry/exit detection
* Duration measurement
* One abnormal behaviour rule
* Timestamped event generation
* Evidence frame
* JSON event output
* Basic Streamlit dashboard

### Stretch Goals

* Multiple abnormal behaviour types
* General anomaly detection
* Crowd behaviour analysis
* Object-specific safety events
* Multiple restricted zones
* Long-video processing
* Automated event summaries
* Improved robustness under occlusion
* Real-time camera input

Stretch features will only be added after the MVP is stable.

---

## 17. Limitations

The initial system is a prototype and has several limitations:

* Behaviour recognition is initially rule-based for the MVP.
* Detection and tracking performance depends on video quality.
* Severe occlusion may affect tracking.
* Camera angle and lighting can influence detection.
* The restricted zone must initially be configured for the scene.
* The MVP focuses on a limited set of behaviours rather than general human behaviour understanding.

These limitations will be considered when evaluating system performance.

---

## 18. External Resources

All external resources used by the project will be documented in:

```text
docs/resources.md
```

This includes:

* Pretrained models
* Datasets
* Open-source libraries
* APIs
* External implementations
* Relevant licenses

No external component will be presented as original work.

---

## 19. Team Contributions

### CSE

* Computer vision pipeline
* Detection
* Tracking
* Behaviour implementation
* Dashboard and software integration

### Food Processing & Engineering

* Industrial and food-processing safety scenarios
* Definition of meaningful abnormal behaviour
* Critical/restricted-area validation
* Domain-based test cases
* Food-industry applicability

### Aerospace Engineering

* Safety-critical event analysis
* Tracking and reliability testing
* Occlusion and edge-case testing
* Safety-oriented system evaluation

---

## 20. Hackathon Scope

SafeTrack AI is being developed as a working prototype for:

**HNX26PSI07 – Autonomous Vision & Behaviour Understanding**

The project prioritizes:

* A working system
* Explainable behaviour analysis
* Reliable tracking
* Meaningful event detection
* Timestamped evidence
* Reproducible implementation
* Clear documentation

---

## 21. Future Vision

The long-term goal is to extend SafeTrack AI from a single rule-based safety event into a broader behaviour-understanding platform capable of monitoring complex environments such as:

* Food processing facilities
* Manufacturing plants
* Laboratories
* Warehouses
* Campuses
* Transport facilities
* Other safety-critical environments

The system can progressively move from predefined behaviour rules toward more general behaviour and anomaly understanding.

---

## License

This project is released under the **MIT License**. See [`LICENSE`](LICENSE) for details.
