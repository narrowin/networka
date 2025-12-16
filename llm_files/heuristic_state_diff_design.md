# Heuristic Operational State Diffing - Design & Implementation

## Overview

This document outlines the design and implementation of the heuristic-based operational state diffing feature for `networka`. The goal is to provide meaningful diffs for unstructured network CLI output (e.g., `show` commands) by treating text as structured, identity-keyed data rather than raw lines.

## Core Philosophy

The solution avoids ML/LLMs and relies on deterministic heuristics inspired by industry-standard tools:

1.  **diffios**: Hierarchical block segmentation via indentation.
2.  **netcompare**: Set-based comparison (identity over order).
3.  **pyATS/Genie**: Canonicalization of volatile fields.

## Architecture

The implementation is modularized into `src/network_toolkit/api/state_diff.py` and `src/network_toolkit/api/state_diff_patterns.py`.

### 1. Pattern Repository (`state_diff_patterns.py`)

Centralizes compiled regex patterns to ensure consistency and easy updates.

*   **Volatile Fields**:
    *   **Timestamps**: ISO, US format, Cisco "timestamp abs first", etc.
    *   **Uptimes**: "1 year, 2 weeks", "12:34:56", "up for ...".
    *   **Counters**: Packet/byte counts, rates (bps/pps), large numbers with commas.
    *   **IDs**: Session IDs, sequence numbers, transaction IDs.
*   **Entity Extraction**:
    *   **Interfaces**: `GigabitEthernet1/0/1`, `Vlan10`, `Port-channel1`.
    *   **IP Routes**: `10.0.0.0/24`, `0.0.0.0/0`.
    *   **BGP Neighbors**: `neighbor 1.2.3.4`.
    *   **MAC Addresses**: Standard formats.
*   **Structure**:
    *   **Table Detection**: Separator lines (`---`, `===`), header rows.
    *   **Ignore Lines**: Banners, "building configuration", pagination prompts.

### 2. Logic Pipeline (`state_diff.py`)

The `StateDiffer` class orchestrates the diffing process through four stages:

#### A. Block Segmentation (`BlockSegmenter`)
*   **Logic**: Uses indentation to infer hierarchy.
    *   Lines starting with no whitespace are **Parents/Headers**.
    *   Indented lines are **Children**.
*   **Output**: A list of blocks, where each block is a list of lines (header + children).

#### B. Entity Extraction (`EntityExtractor`)
*   **Logic**: Analyzes the header line of each block to find a stable identifier.
*   **Priority**:
    1.  Specific regex matches (Interface, BGP, Route, MAC).
    2.  Generic fallback: First few words if they look like an ID (e.g., "VLAN 10").
    3.  "Unknown Block N" if no identity is found.

#### C. Canonicalization (`Canonicalizer`)
*   **Logic**: Replaces volatile fields in *all* lines with stable placeholders.
    *   `uptime is 1 week, 2 days` -> `uptime is <UPTIME>`
    *   `5 minute input rate 1000 bits/sec` -> `5 minute input rate <COUNTER> bits/sec`
*   **Purpose**: Ensures that changes in noise (counters, time) do not trigger a diff.

#### D. Set-Based Diffing (`StateDiffer.diff`)
*   **Logic**:
    1.  Build a map: `{Identity -> Canonicalized_Content}` for both Pre and Post states.
    2.  **Added**: Identity exists in Post but not Pre.
    3.  **Removed**: Identity exists in Pre but not Post.
    4.  **Modified**: Identity exists in both, but canonicalized content differs.
*   **Fuzzy Matching**: For modified blocks, `difflib.SequenceMatcher` is used to classify changes:
    *   **High Confidence**: Clear additions/removals of lines.
    *   **Low Confidence**: Lines that are very similar (ratio > 0.8) but not identical (possible missed volatile field).

## Integration

### CLI Command (`nw diff`)

The feature is exposed via the `--heuristic` / `-H` flag.

```bash
# Diff local files
nw diff pre.txt post.txt --heuristic

# Diff device command against baseline
nw diff sw-core1 "/show interface status" --baseline baseline/ --heuristic
```

### Output Format

The output is structured to guide the operator:

*   **HIGH CONFIDENCE**: Structural changes (Added/Removed entities) or clear configuration changes.
*   **LOW CONFIDENCE**: Minor text variations that might be churn.
*   **IGNORED**: Summary of lines skipped due to volatility (if verbose).

## Future Improvements

1.  **Genealogy**: Support deeper nesting (Grandparent -> Parent -> Child) for complex configs like QoS.
2.  **User Templates**: Allow users to define custom regex patterns for their specific environment.
3.  **JSON Output**: Structured JSON output for programmatic consumption of the diff result.
