"""
Eugene W. Myers, "An O(ND) Difference Algorithm and Its Variations",
Algorithmica 1, 251-266 (1986).

Implements the paper's core greedy LCS/SES algorithm (Section 2, the
O(ND) time / O(ND) space version - not the linear-space divide-and-conquer
refinement from Section 4b, which isn't needed at the string lengths
involved here: usernames, account identifiers, and personal names, all a
handful of characters). For two sequences a, b of length N and M, it finds
the length D of the shortest edit script (using only single-element
insertions and deletions, no substitutions) that turns a into b, by
searching successive "D-paths" through the edit graph until one reaches
the bottom-right corner.

Used here for entity resolution (see run_case_export.py): matching an
ApplicationAccount's raw identifier (e.g. iSmartAlarm's "JPinkman") against
a known suspect's real name (e.g. "Jessie Pinkman") by character-level
similarity, to support an evidence-backed "ownedBy" link with a confidence
score.
"""


def myers_diff(a: str, b: str) -> int:
    """Returns D, the length of the shortest edit script (# of single-char
    insertions/deletions) needed to turn `a` into `b`. Equivalent to the
    classic Levenshtein distance restricted to insert/delete only (no
    substitution)"""
    n, m = len(a), len(b)
    if n == 0:
        return m
    if m == 0:
        return n

    max_d = n + m
    # v[k] = the furthest-reaching x coordinate on diagonal k for the
    # current number of edits considered so far ("D-path" front, per the
    # paper's Section 2 presentation).
    v = {1: 0}

    for d in range(max_d + 1):
        for k in range(-d, d + 1, 2):
            if k == -d or (k != d and v.get(k - 1, -1) < v.get(k + 1, -1)):
                x = v.get(k + 1, 0)
            else:
                x = v.get(k - 1, 0) + 1
            y = x - k

            # Follow any free diagonal moves (matching characters) --
            # the "snake" in the paper's terminology.
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1

            v[k] = x

            if x >= n and y >= m:
                return d

    return max_d  # unreachable for finite sequences


def similarity_ratio(a: str, b: str) -> float:
    """Normalizes Myers' edit distance into a 0..1 similarity score:
    1.0 for identical strings, 0.0 for two strings sharing no common
    subsequence at all. Comparison is case-insensitive, since the
    usernames/identifiers being matched against real names differ in
    case for reasons that have nothing to do with identity (e.g.
    "JPinkman" vs "Jessie Pinkman")."""
    a, b = a.lower(), b.lower()
    if not a and not b:
        return 1.0
    d = myers_diff(a, b)
    return 1.0 - (d / (len(a) + len(b)))
