"""Tests for the gap and bound math of the traffic measurement."""

from network_toolkit import traffic

MS = 1_000_000


def test_gap_bounds_window_and_baseline():
    # Stream 7 sends seq 0 to 49 every 100 ms. The replies of seq 40 and 41 are lost.
    a = "h1:eth1"
    b = "h2:eth1"
    sent: traffic.Frames = {}
    received: traffic.Frames = {}
    for seq in range(50):
        stamp = seq * 100 * MS
        sent[7, 8, seq] = [stamp]
        received[7, 8, seq] = [stamp + MS]
        if seq not in (40, 41):
            received[7, 0, seq] = [stamp + MS]
            sent[7, 0, seq] = [stamp + 2 * MS]
    received[7, 8, 10].append(10 * 100 * MS + 3 * MS)
    windows = [
        traffic.Window("baseline", 0, 3900 * MS),
        traffic.Window("down", 3900 * MS, 5000 * MS),
    ]
    result = traffic.measure_frames(
        {a: sent, b: received}, [traffic.Stream(7, a, b, 0.1)], windows
    )

    flow = result["streams"]["7"]
    assert flow["lost"] == [40, 41]
    assert flow["duplicates"] == [10]
    assert flow["cadence_ok"] is True
    [gap] = flow["gaps"]
    assert gap["first_seq"] == 40
    assert gap["last_seq"] == 41
    assert gap["lost"] == 2
    assert gap["lower_s"] == 0.1
    assert gap["upper_s"] == 0.3
    assert gap["window"] == "down"
    down = result["windows"]["down"]["streams"]["7"]
    assert down["outage"] == {"lower_s": 0.1, "upper_s": 0.3, "lost": 2}
    assert result["windows"]["baseline"]["streams"]["7"]["outage"] is None
    assert traffic.baseline(result, "baseline", {"7": 30})["verdict"] == "fail"
