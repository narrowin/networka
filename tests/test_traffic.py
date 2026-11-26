"""Tests for the gap and bound math of the traffic measurement."""

from network_toolkit import traffic

MS = 1_000_000


def test_gap_bounds_window_and_quiet_window():
    # Stream 7 sends seq 0 to 49 every 100 ms. The replies of seq 40 and 41 are lost.
    a = "h1:eth1"
    b = "h2:eth1"
    payload = b"echo payload"
    sent: traffic.Frames = {}
    received: traffic.Frames = {}
    for seq in range(50):
        stamp = seq * 100 * MS
        probe = (seq, payload)
        sent[7, 8, probe] = [stamp]
        received[7, 8, probe] = [stamp + MS]
        if seq not in (40, 41):
            received[7, 0, probe] = [stamp + MS]
            sent[7, 0, probe] = [stamp + 2 * MS]
    received[7, 8, (10, payload)].append(10 * 100 * MS + 3 * MS)
    windows = [
        traffic.Window("quiet window", 0, 3900 * MS),
        traffic.Window("down", 3900 * MS, 5000 * MS),
    ]
    result = traffic.measure_frames(
        {a: sent, b: received}, [traffic.Stream("h1-to-h2", 7, a, b)], windows
    )

    flow = result["streams"]["h1-to-h2"]
    assert flow["lost_seqs"] == [40, 41]
    assert flow["duplicates"] == [10]
    assert flow["cadence_ok"] is True
    [gap] = flow["gaps"]
    assert gap["first_seq"] == 40
    assert gap["last_seq"] == 41
    assert gap["lost"] == 2
    assert gap["lower_s"] == 0.1
    assert gap["upper_s"] == 0.3
    assert gap["windows"] == ["down"]
    down = result["windows"]["down"]["streams"]["h1-to-h2"]
    assert down["outage"] == {"lower_s": 0.1, "upper_s": 0.3, "lost": 2}
    assert down["summary"] == (
        "2 pings lost at one ping every 100 ms, traffic stopped for 0.1 to 0.3 s"
    )
    assert result["windows"]["quiet window"]["streams"]["h1-to-h2"]["outage"] is None
    # The duplicate of seq 10 breaks the quiet window rule.
    assert traffic.quiet(result, "quiet window")["verdict"] == "fail"


def test_kernel_drops_reads_the_tcpdump_summary() -> None:
    log = "listening on bond0\n120 packets captured\n120 packets received by filter\n0 packets dropped by kernel\n"
    assert traffic.kernel_drops(log) == 0
    assert traffic.kernel_drops("listening on bond0\n") is None
