# Real-video evaluation protocol

This document is a test plan, not a claim of measured model performance.

Use consented footage and manually annotate actual event intervals and visible entity tracks before running the application. Keep expected annotations separate from generated results. Record model version, hardware, sampling interval, segment length, codec, and video duration.

| Scenario | Evidence to record | Check |
|---|---|---|
| Short activity sequence | Three actual actions and manually reviewed onset/offset | Correct descriptions, chronological first/next/last |
| Repeated action | Distinct starts/stops of the same visible machine or object | No duplicate counting of continuous intervals; count and every occurrence timestamp |
| Events close together | Actions separated by less than the sample interval | Report missed/ambiguous events; reduce interval and compare |
| Duration | Visible entry/activity/exit bounds | Compare interval duration; avoid equating track span with occupancy |
| Gap | Two independently annotated events | `start(B) - end(A)`, including overlap/reverse-order cases |
| Multiple people/objects | Separately annotated identities in each sampled frame | Identity switches, uncertain associations and track fragmentation |
| Temporary occlusion | Object blocked then visible again | Association across short gaps; uncertainty when ambiguous |
| Leaves and re-enters | Appearance evidence before and after a known absence | Short-gap association; do not claim guaranteed identity after long absence |
| Moving camera | Pan/zoom, then viewpoint change or scene cut | Motion compensation quality and failure visibility |
| Long recording | Events across several chunk boundaries | Global timestamp alignment; bounded image memory; counts across all chunks |
| Stationary object | Visible motion and interactions annotated manually | Stationary is not "untouched"; refuse unsupported absence-of-interaction claims |
| Restricted-area scenario | Record actual entry/exit and any visible indicator change | Use observed descriptions; no invented zone violation or audible alarm |
| False temporal premise | A occurs before B; ask who did A after B | Reject the premise with B's evidence timestamp; do not reverse order |
| Unsupported observation | Ask about a sound, cause, hidden action or real-world identity | Explicit insufficient evidence with video coverage timestamps |

Measure event precision/recall, start/end absolute error, duration error, occurrence-count error, track identity switches, fragmentation, and answer correctness against human annotations. Report results separately for sampled visual evidence and full footage. Nearest-observed before/after is weaker than proving immediate succession in all frames.

Do not use an example prompt as a ground-truth annotation. Do not mark a detector test passed just because an API returned JSON. Each factual claim must be checked against the supplied footage.
