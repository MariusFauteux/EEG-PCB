"""Host-side reference for EVENT record timing (recording format v1, event schema 1).

Firmware captures DRDY, trigger and photodiode edges on one MCU timer, so an event's position on the ADC
sample timeline follows from timer ticks alone; the ADC and MCU clocks never need to agree in frequency.

Timeline convention: sample k is reported by DRDY edge k at tick t_k. Its input-referred instant is
t_k - D*T, where T is the sample period in ticks and D the ADC group delay in samples (1.5 for the sinc3
filter by derivation; replace with the bench-calibrated value). An event captured at tick t_e with fixed
input-path latency L ticks therefore sits at fractional sample position

    x = k + (t_e - L - t_k) / T + D

so an event coincident with sample k's input-referred instant yields x = k.
"""
from dataclasses import dataclass

SCHEMA = 'event/1'
SOURCES = {'trigger', 'photodiode', 'record_button'}
KINDS = {'edge', 'clock_sync'}
NOMINAL_GROUP_DELAY_SAMPLES = 1.5


def validate(event):
    """Check the required fields of an EVENT payload; raises ValueError."""
    if event.get('schema') != SCHEMA:
        raise ValueError('unsupported event schema')
    kind = event.get('kind')
    if kind not in KINDS:
        raise ValueError('unknown event kind')
    for field in ('tick', 'tick_hz', 'drdy_index', 'drdy_tick'):
        if not isinstance(event.get(field), int) or event[field] < 0:
            raise ValueError(f'{field} must be a non-negative integer')
    if event['tick_hz'] == 0:
        raise ValueError('tick_hz must be positive')
    if kind == 'edge':
        if event.get('source') not in SOURCES:
            raise ValueError('unknown event source')
        if event.get('level_after') not in (0, 1):
            raise ValueError('level_after must be 0 or 1')
        if event['tick'] < event['drdy_tick']:
            raise ValueError('event precedes its reference DRDY')
        nxt = event.get('drdy_next_tick')
        if nxt is not None and (not isinstance(nxt, int) or nxt <= event['drdy_tick']):
            raise ValueError('drdy_next_tick must follow drdy_tick')
    return event


@dataclass
class ClockFit:
    period_ticks: float      # ticks per ADC sample
    offset_ticks: float      # tick of sample index 0 (DRDY)
    rate_hz: float           # ADC sample rate measured against the MCU timebase
    ppm_vs_nominal: float
    max_residual_ticks: float


def fit_clock(sync_events, nominal_rate_hz=1000.0):
    """Least-squares fit of DRDY tick against sample index from clock_sync (or any) events."""
    pts = [(e['drdy_index'], e['drdy_tick']) for e in sync_events]
    if len(pts) < 2:
        raise ValueError('need at least two sync points')
    hz = sync_events[0]['tick_hz']
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx == 0:
        raise ValueError('sync points share one sample index')
    slope = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    offset = my - slope * mx
    rate = hz / slope
    resid = max(abs(p[1] - (offset + slope * p[0])) for p in pts)
    return ClockFit(slope, offset, rate, (rate / nominal_rate_hz - 1) * 1e6, resid)


def sample_position(event, group_delay_samples=NOMINAL_GROUP_DELAY_SAMPLES, latency_ticks=0, fit=None):
    """Fractional ADC sample position of an edge event on the input-referred timeline."""
    validate(event)
    if event['kind'] != 'edge':
        raise ValueError('only edge events have a sample position')
    if event.get('drdy_next_tick') is not None:
        period = event['drdy_next_tick'] - event['drdy_tick']
    elif fit is not None:
        period = fit.period_ticks
    else:
        raise ValueError('period unknown: provide drdy_next_tick or a clock fit')
    return event['drdy_index'] + (event['tick'] - latency_ticks - event['drdy_tick']) / period + group_delay_samples


def sample_position_from_fit(event, fit, group_delay_samples=NOMINAL_GROUP_DELAY_SAMPLES, latency_ticks=0):
    """Position using only the session clock fit (robust to a single mistimed DRDY capture)."""
    validate(event)
    return (event['tick'] - latency_ticks - fit.offset_ticks) / fit.period_ticks + group_delay_samples
