import unittest

import event_timing as et

TICK_HZ = 16_000_000


def drdy_tick(k, rate_hz, start=12_345):
    return start + round(k * TICK_HZ / rate_hz)


def edge(t, k, rate_hz, source='trigger', with_next=True):
    e = {'schema': et.SCHEMA, 'kind': 'edge', 'source': source, 'level_after': 0, 'tick': t,
         'tick_hz': TICK_HZ, 'drdy_index': k, 'drdy_tick': drdy_tick(k, rate_hz)}
    e['drdy_next_tick'] = drdy_tick(k + 1, rate_hz) if with_next else None
    return e


class EventTiming(unittest.TestCase):
    def test_event_at_input_referred_instant_maps_to_index(self):
        rate = 1000.0
        k = 500
        period = TICK_HZ / rate
        t = drdy_tick(k, rate) - round(1.5 * period)   # input-referred instant of sample k
        # the event is referenced to the DRDY at or before it: k - 2 for a 1.5-sample delay
        ref = k - 2
        x = et.sample_position(edge(t, ref, rate))
        self.assertAlmostEqual(x, k, places=3)

    def test_fraction_between_samples(self):
        rate = 1000.0
        t = drdy_tick(10, rate) + 4000            # quarter period after DRDY 10
        x = et.sample_position(edge(t, 10, rate), group_delay_samples=0)
        self.assertAlmostEqual(x, 10.25, places=6)

    def test_latency_is_subtracted(self):
        rate = 1000.0
        t = drdy_tick(10, rate) + 4000
        x = et.sample_position(edge(t, 10, rate), group_delay_samples=0, latency_ticks=1600)
        self.assertAlmostEqual(x, 10.15, places=6)

    def test_clock_fit_recovers_offset_ppm(self):
        rate = 1000.0 * (1 + 20e-6)                # +20 ppm ADC clock
        sync = [{'schema': et.SCHEMA, 'kind': 'clock_sync', 'tick': drdy_tick(k, rate), 'tick_hz': TICK_HZ,
                 'drdy_index': k, 'drdy_tick': drdy_tick(k, rate)} for k in range(0, 3_600_000, 1000)]
        fit = et.fit_clock(sync)
        self.assertAlmostEqual(fit.ppm_vs_nominal, 20.0, delta=0.01)
        self.assertLessEqual(fit.max_residual_ticks, 1.0)  # integer-tick quantisation

    def test_internal_clock_error_is_visible_without_fit(self):
        # A 2.5 % slow clock: assuming nominal 1 kHz misplaces an event 1 s into an epoch by ~25 ms.
        rate = 975.0
        t = drdy_tick(975, rate)
        true_seconds = (t - drdy_tick(0, rate)) / TICK_HZ
        nominal_seconds = 975 / 1000.0
        self.assertGreater(abs(true_seconds - nominal_seconds) * 1e3, 24.0)

    def test_fit_used_when_next_drdy_missing(self):
        rate = 1000.0
        sync = [{'schema': et.SCHEMA, 'kind': 'clock_sync', 'tick': drdy_tick(k, rate), 'tick_hz': TICK_HZ,
                 'drdy_index': k, 'drdy_tick': drdy_tick(k, rate)} for k in (0, 1000, 2000)]
        fit = et.fit_clock(sync)
        e = edge(drdy_tick(1500, rate) + 8000, 1500, rate, with_next=False)
        self.assertAlmostEqual(et.sample_position(e, fit=fit, group_delay_samples=0), 1500.5, places=3)
        self.assertAlmostEqual(et.sample_position_from_fit(e, fit, group_delay_samples=0), 1500.5, places=3)
        with self.assertRaises(ValueError):
            et.sample_position(e)

    def test_schema_rejections(self):
        good = edge(drdy_tick(3, 1000.0) + 10, 3, 1000.0)
        for field, value in [('schema', 'event/0'), ('source', 'mains'), ('level_after', 2), ('tick', -1),
                             ('tick_hz', 0), ('tick', 0)]:
            bad = dict(good, **{field: value})
            with self.assertRaises(ValueError, msg=field):
                et.validate(bad)


if __name__ == '__main__':
    unittest.main()
