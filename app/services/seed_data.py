"""
Seed data generator and loader for the Hydraulic Press 07 demo bundle.
"""

from pathlib import Path
from app.config import SEEDED_DIR
from app.models.schemas import Asset
from app.services.transcription import generate_synthetic_operator_wav


PRESS_07_ASSET = Asset(
    asset_id="press-07",
    display_name="Hydraulic Press 07 (HP-750)",
    timezone="Europe/Rome",
    signals=["motor_temperature", "vibration_rms", "hydraulic_pressure"],
    baseline_metrics={
        "motor_temperature": {
            "unit": "°C",
            "nominal_min": 50.0,
            "nominal_max": 80.0,
            "trip_max": 85.0
        },
        "vibration_rms": {
            "unit": "mm/s",
            "nominal_min": 0.5,
            "nominal_max": 3.2,
            "trip_max": 4.5
        },
        "hydraulic_pressure": {
            "unit": "bar",
            "nominal_min": 190.0,
            "nominal_max": 230.0,
            "trip_min": 170.0
        }
    }
)

CSV_CONTENT = """timestamp,asset_id,signal,value,unit
2026-10-13T06:15:00+02:00,press-07,motor_temperature,62.4,°C
2026-10-13T06:15:00+02:00,press-07,vibration_rms,2.1,mm/s
2026-10-13T06:15:00+02:00,press-07,hydraulic_pressure,205.0,bar
2026-10-13T07:30:00+02:00,press-07,motor_temperature,74.8,°C
2026-10-13T07:30:00+02:00,press-07,vibration_rms,2.3,mm/s
2026-10-13T08:22:10+02:00,press-07,motor_temperature,86.5,°C
2026-10-13T08:45:00+02:00,press-07,motor_temperature,82.0,°C
2026-10-13T09:40:15+02:00,press-07,hydraulic_pressure,162.0,bar
2026-10-13T09:50:00+02:00,press-07,hydraulic_pressure,208.0,bar
2026-10-13T10:45:30+02:00,press-07,motor_temperature,88.2,°C
2026-10-13T11:15:20+02:00,press-07,vibration_rms,4.8,mm/s
2026-10-13T11:30:00+02:00,press-07,vibration_rms,2.8,mm/s
2026-10-13T12:15:00+02:00,press-07,motor_temperature,83.5,°C
2026-10-13T13:10:45+02:00,press-07,motor_temperature,91.4,°C
2026-10-13T13:45:00+02:00,press-07,motor_temperature,89.0,°C
2026-10-13T13:45:00+02:00,press-07,hydraulic_pressure,202.0,bar
"""

MAINTENANCE_NOTES_CONTENT = """# Maintenance Shift Handover Log - Press 07
Technician: Sarah Jenkins (Shift A Lead)
Logged: 2026-10-13T04:30:00+02:00

## Action Item 1: Inline Filter Replacement
- Replaced primary 10-micron hydraulic filter cartridge (Part #HP-FLT-10M) due to elevated differential pressure indicator.
- Topped up reservoir with 15 liters of Mobil DTE 25 ISO VG 46 hydraulic fluid.
- System pressurized and inspected for fitting leaks; zero active leaks detected.
- SOP Note: Run-in procedure requires monitoring line pressure stability and filter differential pressure for the first 8 operating hours.

## Action Item 2: Secondary Cooling Inspection
- Visually inspected heat exchanger secondary supply hose and cleaned strainer basket.
- Note for Shift B: Minor calcification noted on exterior flange; recommend flushing circuit if motor thermal alerts recur.
"""

MANUAL_CONTENT = """# Equipment Operating Manual: Hydraulic Press HP-750 (Asset: press-07)
Manufacturer: Industrial Forming Systems S.p.A.
Document Ref: IFS-HP750-REV4

<!-- Page: 2 -->
# Section 1.0 General Specifications & Nominal Envelope
The IFS HP-750 hydraulic press operates at a nominal clamping force of 750 metric tons.
Nominal hydraulic operating pressure: 190 to 230 bar.
Nominal main drive motor temperature: 50.0 to 80.0 °C. Continuous duty trip threshold: 85.0 °C.
Nominal vibration velocity: 0.5 to 3.2 mm/s RMS. Alarm trip limit: 4.5 mm/s RMS.

<!-- Page: 8 -->
# Section 2.3 Fluid Management & Inline Filter Cartridge Maintenance
After installing a replacement filter cartridge, initial micro-settling of the filter media may cause transient differential pressure readings.
Operators and maintenance technicians must observe the line pressure stability for the first 8 operating hours following replacement.
Do not adjust the primary relief valve setting until the oil has reached steady operating temperature (50 °C).

<!-- Page: 14 -->
# Section 4.2 Thermal Overload, Cooling Path Troubleshooting & Heat Exchanger Maintenance
If main drive motor temperature exceeds the 85.0 °C trip limit repeatedly during standard cycle loads:
1. Verify secondary cooling circuit water flow rate is at or above 45 liters/minute.
2. Check differential temperature between heat exchanger inlet and outlet (normal drop: 12-16 °C).
3. If temperature exceeds 90 °C, pause non-critical high-tonnage cycles. Inspect heat exchanger plate channels for mineral scaling or sediment restriction.
4. Execute Procedure SOP-M42: Isolate secondary cooling circuit, flush with approved citric descaling agent, and inspect thermal control modulating valve.

<!-- Page: 22 -->
# Section 7.1 Vibration Limits, Cavitation Relief & Suction Manifold Checks
Vibration RMS spikes exceeding 4.5 mm/s indicate abnormal mechanical surge or hydraulic cavitation.
If a vibration spike occurs concurrently with sudden line pressure drops (below 170 bar):
1. Immediately inspect suction manifold valve seating and suction pipe seals for air ingress.
2. Verify oil reservoir level gauge is above the minimum mark (low fluid level introduces air aeration into pump intake).
3. Check pump shaft coupling alignment and torque bolts according to table 7.3.
"""

TRANSCRIPT_JSON_CONTENT = """{
  "text": "Marco (Outgoing Operator Shift B): Shift handover memo for Hydraulic Press 07 at 13:20. We noticed an intermittent high-pitch whine around the main heat exchanger, and the motor casing felt hot to touch around 10:30. Keep an eye on the cooling circuit, and check the line pressure if vibration spikes again. Filter cartridge was replaced earlier on Shift A.",
  "segments": [
    {
      "start": 0.0,
      "end": 4.5,
      "text": "Marco (Outgoing Operator Shift B): Shift handover memo for Hydraulic Press 07 at 13:20.",
      "speaker": "Marco"
    },
    {
      "start": 4.5,
      "end": 12.0,
      "text": "We noticed an intermittent high-pitch whine around the main heat exchanger, and the motor casing felt hot to touch around 10:30.",
      "speaker": "Marco"
    },
    {
      "start": 12.0,
      "end": 18.5,
      "text": "Keep an eye on the cooling circuit, and check the line pressure if vibration spikes again. Filter cartridge was replaced earlier on Shift A.",
      "speaker": "Marco"
    }
  ],
  "confidence": 0.94,
  "engine": "Built-in Industrial Acoustic Adapter (ROCm compatible)"
}"""


def create_seeded_bundle_files():
    """Generates the bundle files on disk if they don't already exist."""
    csv_path = SEEDED_DIR / "shift_b_telemetry.csv"
    maint_path = SEEDED_DIR / "maintenance_notes_shift_a.md"
    manual_path = SEEDED_DIR / "hydraulic_press_07_sop_manual.md"
    transcript_path = SEEDED_DIR / "operator_voice_transcript.json"
    wav_path = SEEDED_DIR / "operator_voice_memo.wav"

    if not csv_path.exists():
        csv_path.write_text(CSV_CONTENT, encoding="utf-8")
    if not maint_path.exists():
        maint_path.write_text(MAINTENANCE_NOTES_CONTENT, encoding="utf-8")
    if not manual_path.exists():
        manual_path.write_text(MANUAL_CONTENT, encoding="utf-8")
    if not transcript_path.exists():
        transcript_path.write_text(TRANSCRIPT_JSON_CONTENT, encoding="utf-8")
    if not wav_path.exists():
        generate_synthetic_operator_wav(wav_path, duration_seconds=6.0)
