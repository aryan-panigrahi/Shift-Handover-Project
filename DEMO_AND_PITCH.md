---
title: Shift Handover Briefing Demo and Pitch
type: presentation
status: draft
updated: 2026-10-13
---

# Demo and Pitch

## Demo scenario

**Asset:** Hydraulic Press 07 (synthetic). **Shift:** 06:00–14:00. The bundle contains repeated rising motor temperature, a brief vibration spike, an operator memo mentioning an unusual sound, a maintenance note that a filter was replaced, and a relevant manual passage describing a cooling-path inspection. The exact values and manual excerpt must be synthetic or permissioned and internally consistent.

## Three-minute walkthrough

1. **Problem (20 sec):** “The incoming shift has logs, notes, a voice memo, and a long manual. Important context is scattered.”
2. **Inputs (30 sec):** Load the synthetic shift bundle; show source coverage and the transcribed memo.
3. **Handover (60 sec):** Generate a live briefing. Open the top item to show the repeated temperature event, the operator note, and the manual page citation. Show ranking factors and an explicit uncertainty.
4. **Human review (30 sec):** Edit/acknowledge the suggested check. Emphasize it is a draft for the technician, not machine control or a substitute for SOP.
5. **Runtime proof (20 sec):** Show whether the configured endpoint is reachable and whether the latest synthesis completed through it. Only describe AMD ROCm hardware if the endpoint host has independently verified it; otherwise demonstrate the deterministic local fallback.
6. **Outcome (20 sec):** Compare manual baseline time with assisted draft time on the same scenario; state the measured result and sample size honestly.

## Pitch outline

- **Problem:** Shift-critical knowledge is fragmented across machine data, notes, voice, and manuals.
- **Product:** One evidence-linked, prioritized handover in minutes.
- **Why it helps:** Less time reconciling sources; clearer context and follow-up for the next shift.
- **How it works:** Normalize source events, retrieve manual evidence, rank transparently, synthesize through an optional remote endpoint or deterministic local fallback, and keep operator approval.
- **Differentiator:** Every important statement is traceable to a source, and uncertainty is visible.
- **AMD role:** An AMD ROCm-hosted endpoint can be configured for core synthesis. The repository default is local deterministic fallback, so the presenter must configure and verify the endpoint before making a live AMD claim.
- **Proof:** Show coverage, citation checks, event recall, and measured preparation-time comparison.
- **Next step:** Integrate one real, sanitized equipment data source with a pilot maintenance team.

## Demo data checklist

- [x] Label the bundle synthetic.
- [x] Include at least one repeated signal, one operator observation, one maintenance note, and one manual citation.
- [x] Seed one misleading/ambiguous observation to demonstrate uncertainty handling.
- [x] Prepare expected event ranking and valid source locator list.
- [x] Ensure the displayed manual citation really contains the referenced guidance.
- [ ] Record live endpoint metadata and a backup recording.

The seeded WAV is synthetic audio with a canned transcript. Call this out during the
demo; it is not a speech-recognition result unless a remote transcription service is
configured and returns the transcript.
