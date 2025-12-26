"""Heuristic operational state diffing logic.

This module implements a deterministic, heuristic-based approach to diffing
unstructured network CLI output. It treats text as structured, identity-keyed
data rather than raw lines.

Key components:
- Canonicalizer: Normalizes volatile fields (timestamps, counters).
- BlockSegmenter: Detects logical blocks via indentation/headers.
- EntityExtractor: Infers stable identifiers (interfaces, IPs).
- SetDiffer: Compares entities as sets (Added/Removed/Modified).
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from network_toolkit.api.state_diff_patterns import (
    BGP_NEIGHBOR_IDENTITY_PATTERN,
    COUNTER_PATTERNS,
    IGNORE_PATTERNS,
    INTERFACE_IDENTITY_PATTERN,
    MAC_ADDRESS_PATTERN,
    ROUTE_IDENTITY_PATTERN,
    TIMESTAMP_PATTERNS,
    UPTIME_PATTERNS,
    VOLATILE_ID_PATTERNS,
)


@dataclass
class HeuristicDiffOutcome:
    """Result of a heuristic diff operation."""

    high_confidence: list[str] = field(default_factory=list)
    low_confidence: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    summary: str = ""

    def to_string(self) -> str:
        """Format the diff result as a human-readable string."""
        parts = []
        if self.high_confidence:
            parts.append("HIGH CONFIDENCE CHANGES:")
            parts.extend(f"  {line}" for line in self.high_confidence)
            parts.append("")

        if self.low_confidence:
            parts.append("LOW CONFIDENCE CHANGES (Possible Churn):")
            parts.extend(f"  {line}" for line in self.low_confidence)
            parts.append("")

        if self.ignored:
            parts.append("IGNORED (Volatile/Noise):")
            # Summarize ignored lines if too many
            if len(self.ignored) > 10:
                parts.append(
                    f"  {len(self.ignored)} lines (timestamps, counters, etc.)"
                )
            else:
                parts.extend(f"  {line}" for line in self.ignored)
            parts.append("")

        if not parts:
            return "No significant operational state changes detected."

        return "\n".join(parts).strip()


class Canonicalizer:
    """Normalizes volatile fields in text lines."""

    def normalize(self, line: str) -> str:
        """Replace volatile fields with placeholders."""
        # 1. Check ignore patterns first
        for pattern in IGNORE_PATTERNS:
            if pattern.search(line):
                return ""  # Mark for removal

        # 2. Normalize timestamps
        for pattern in TIMESTAMP_PATTERNS:
            line = pattern.sub("<TIME>", line)

        # 3. Normalize uptimes
        for pattern in UPTIME_PATTERNS:
            line = pattern.sub("<UPTIME>", line)

        # 4. Normalize counters
        for pattern in COUNTER_PATTERNS:
            line = pattern.sub("<COUNTER>", line)

        # 5. Normalize volatile IDs
        for pattern in VOLATILE_ID_PATTERNS:
            line = pattern.sub("<ID>", line)

        return line.strip()


class BlockSegmenter:
    """Segments text into logical blocks based on indentation and headers."""

    def segment(self, text: str) -> list[list[str]]:
        """Segment text into hierarchical blocks.

        Returns a list of blocks, where each block is a list of lines.
        The first line of a block is typically the parent/header.
        """
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        blocks: list[list[str]] = []
        current_block: list[str] = []

        for line in lines:
            # Heuristic: Lines starting with space are children
            if line.startswith(" ") or line.startswith("\t"):
                if current_block:
                    current_block.append(line)
                else:
                    # Orphaned child, treat as new block start (fallback)
                    current_block = [line]
            else:
                # Parent line starts new block
                if current_block:
                    blocks.append(current_block)
                current_block = [line]

        if current_block:
            blocks.append(current_block)

        return blocks


class EntityExtractor:
    """Extracts stable identifiers from text blocks."""

    def extract_identity(self, block: list[str]) -> str | None:
        """Attempt to extract a stable identity from the block's header (first line)."""
        if not block:
            return None

        header = block[0]

        # 1. Interface
        match = INTERFACE_IDENTITY_PATTERN.search(header)
        if match:
            return f"Interface {match.group('type')}{match.group('id')}"

        # 2. BGP Neighbor
        match = BGP_NEIGHBOR_IDENTITY_PATTERN.search(header)
        if match:
            return f"BGP Neighbor {match.group('address')}"

        # 3. Route
        match = ROUTE_IDENTITY_PATTERN.search(header)
        if match:
            return f"Route {match.group('prefix')}/{match.group('mask')}"

        # 4. MAC Address
        match = MAC_ADDRESS_PATTERN.search(header)
        if match:
            return f"MAC {match.group(0)}"

        # 5. Generic Key-Value (e.g., "VLAN 10", "VRF blue")
        # Heuristic: First 2-3 words if they look like ID
        parts = header.split()
        if len(parts) >= 2 and parts[1].isdigit():
            return f"{parts[0]} {parts[1]}"

        return None


class StateDiffer:
    """Main class for heuristic operational state diffing."""

    def __init__(self) -> None:
        self.canonicalizer = Canonicalizer()
        self.segmenter = BlockSegmenter()
        self.extractor = EntityExtractor()

    def diff(self, text_a: str, text_b: str) -> HeuristicDiffOutcome:
        """Perform heuristic diff between two text outputs."""
        blocks_a = self.segmenter.segment(text_a)
        blocks_b = self.segmenter.segment(text_b)

        # Map identity -> canonicalized block content
        map_a = self._build_entity_map(blocks_a)
        map_b = self._build_entity_map(blocks_b)

        outcome = HeuristicDiffOutcome()

        # 1. Check for Added/Removed Entities (High Confidence)
        keys_a = set(map_a.keys())
        keys_b = set(map_b.keys())

        added = keys_b - keys_a
        removed = keys_a - keys_b
        common = keys_a & keys_b

        for key in added:
            outcome.high_confidence.append(f"[+] Added: {key}")

        for key in removed:
            outcome.high_confidence.append(f"[-] Removed: {key}")

        # 2. Check for Modified Entities
        for key in common:
            content_a = map_a[key]
            content_b = map_b[key]

            if content_a == content_b:
                continue

            # Deep diff of the block content
            self._diff_block_content(key, content_a, content_b, outcome)

        # 3. Handle Unidentified Blocks (Fallback to line diff)
        # If we couldn't extract identities, we might have put them under "Unknown:..."
        # or we need to handle the raw residue.
        # For now, the _build_entity_map handles "Unknown" keys uniquely.

        return outcome

    def _build_entity_map(self, blocks: list[list[str]]) -> dict[str, list[str]]:
        """Convert blocks to a map of Identity -> Canonicalized Lines."""
        entity_map: dict[str, list[str]] = {}
        unknown_counter = 0

        for block in blocks:
            identity = self.extractor.extract_identity(block)

            # Canonicalize content first to see if anything remains
            norm_lines = []
            for line in block:
                norm = self.canonicalizer.normalize(line)
                if norm:  # Skip empty/ignored lines
                    norm_lines.append(norm)

            if not norm_lines:
                continue

            if not identity:
                # Use canonicalized header as identity if unique enough
                # This ensures that "uptime 1 week" and "uptime 2 weeks" map to same identity
                header = block[0].strip()
                canon_header = self.canonicalizer.normalize(header)

                if canon_header and len(canon_header) > 5:
                    # If we have multiple blocks with same canonical header, append index
                    if canon_header in entity_map:
                        identity = f"{canon_header} #{unknown_counter}"
                        unknown_counter += 1
                    else:
                        identity = canon_header
                else:
                    identity = f"Unknown Block {unknown_counter}"
                    unknown_counter += 1

            entity_map[identity] = norm_lines

        return entity_map

    def _diff_block_content(
        self,
        identity: str,
        lines_a: list[str],
        lines_b: list[str],
        outcome: HeuristicDiffOutcome,
    ) -> None:
        """Compare content of two blocks with same identity."""
        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue

            if tag == "replace":
                # Check if it's just a volatile change that wasn't fully caught
                # or a real change
                for k in range(i2 - i1):
                    old = lines_a[i1 + k]
                    new = lines_b[j1 + k]
                    # If lines are very similar, might be low confidence
                    if difflib.SequenceMatcher(None, old, new).ratio() > 0.8:
                        outcome.low_confidence.append(f"~ {identity}: {old} -> {new}")
                    else:
                        outcome.high_confidence.append(f"~ {identity}: {old} -> {new}")

            elif tag == "delete":
                for k in range(i2 - i1):
                    outcome.high_confidence.append(f"[-] {identity}: {lines_a[i1 + k]}")

            elif tag == "insert":
                for k in range(j2 - j1):
                    outcome.high_confidence.append(f"[+] {identity}: {lines_b[j1 + k]}")
