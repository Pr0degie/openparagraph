"""Three-rule FNA color logic for graph nodes (ARCHITECTURE.md §6).

Rule 1 — FNA-unambiguous: law has FNA code, hard out-edges target a single group
          (or none) → pure main-group hue.
Rule 2 — FNA-bridging: hard out-edges span multiple groups → weighted HSL blend,
          proportional to out-edge counts per group.
Rule 3 — FNA-orphan: no FNA code → weighted HSL blend of soft-edge neighbours'
          colors (equal weights per soft edge).

Processing order: classified (Rules 1+2) first, orphans (Rule 3) second,
so orphan blending can always look up neighbour colors.
"""

import colorsys
import math

# Base HSL palette for the nine FNA Sachgebiet main groups.
# H ∈ [0, 360), S and L ∈ [0, 100].  Chosen for visibility on a dark background.
# Will be superseded once the FNA taxonomy PDF is fully parsed (Stage 05 enrichment).
MAIN_GROUP_HSL: dict[int, tuple[float, float, float]] = {
    1: (224, 90, 62),   # Staatsrecht        → blue
    2: (185, 72, 50),   # Verwaltung         → teal
    3: (350, 80, 55),   # Rechtspflege       → crimson
    4: (35,  88, 58),   # Bürgerliches Recht → amber
    5: (140, 68, 48),   # Wirtschaft         → green
    6: (70,  75, 52),   # Arbeit und Soziales→ yellow-green
    7: (275, 68, 60),   # Finanzen           → violet
    8: (310, 72, 58),   # Verkehr            → magenta
    9: (200, 30, 55),   # Sonstiges          → slate-blue
}

MAIN_GROUP_CLUSTER: dict[int, str] = {
    1: "state-law",
    2: "admin-law",
    3: "justice",
    4: "civil-law",
    5: "commercial-law",
    6: "labor-social",
    7: "finance",
    8: "transport",
    9: "other",
}

ORPHAN_HSL: tuple[float, float, float] = (200, 20, 50)  # neutral slate for isolated orphans
ORPHAN_CLUSTER = "unclassified"


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------


def hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL (h°, s%, l%) to '#rrggbb'."""
    r, g, b = colorsys.hls_to_rgb(h / 360.0, l / 100.0, s / 100.0)
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def blend_hsl(
    colors_weights: list[tuple[tuple[float, float, float], float]],
) -> tuple[float, float, float]:
    """
    Weighted blend of HSL colors.

    Hue: circular mean (avoids 0°/360° discontinuity).
    S and L: linear weighted mean.

    colors_weights: list of ((h, s, l), weight).  Returns (h, s, l).
    """
    total = sum(w for _, w in colors_weights)
    if not colors_weights or total == 0.0:
        return ORPHAN_HSL

    sin_h = sum(math.sin(math.radians(h)) * w for (h, _s, _l), w in colors_weights)
    cos_h = sum(math.cos(math.radians(h)) * w for (h, _s, _l), w in colors_weights)
    hue = math.degrees(math.atan2(sin_h, cos_h)) % 360.0

    sat = sum(s * w for (_h, s, _l), w in colors_weights) / total
    lig = sum(l * w for (_h, _s, l), w in colors_weights) / total

    return (hue, sat, lig)


# ---------------------------------------------------------------------------
# Main assignment logic
# ---------------------------------------------------------------------------


def assign_colors(
    nodes: list[dict],
    edges: list[dict],
    group_hsl: dict[int, tuple[float, float, float]] | None = None,
    group_cluster: dict[int, str] | None = None,
) -> list[dict]:
    """
    Apply three-rule color logic and return an updated copy of nodes.

    Nodes with main_group are processed first (Rules 1+2) so orphan blending
    (Rule 3) can always look up neighbour HSL values.
    """
    if group_hsl is None:
        group_hsl = MAIN_GROUP_HSL
    if group_cluster is None:
        group_cluster = MAIN_GROUP_CLUSTER

    node_map = {n["id"]: n for n in nodes}

    edges_by_source: dict[str, list[dict]] = {}
    for e in edges:
        edges_by_source.setdefault(e["source"], []).append(e)

    hsl_map: dict[str, tuple[float, float, float]] = {}
    color_map: dict[str, str] = {}
    cluster_map: dict[str, str] = {}

    # Pass 1: classified nodes (Rules 1 + 2)
    for node in nodes:
        nid = node["id"]
        own_group: int | None = node["classification"].get("main_group")
        if own_group is None:
            continue

        hard_out = [e for e in edges_by_source.get(nid, []) if e["type"] == "explicit"]

        group_counts: dict[int, int] = {}
        for e in hard_out:
            tgt = node_map.get(e["target"])
            if tgt is None:
                continue
            tgt_group: int | None = tgt["classification"].get("main_group")
            if tgt_group is not None:
                group_counts[tgt_group] = group_counts.get(tgt_group, 0) + 1

        if len(group_counts) <= 1:
            # Rule 1: unambiguous
            hsl = group_hsl.get(own_group, ORPHAN_HSL)
        else:
            # Rule 2: bridging — blend target groups by out-edge count
            pairs = [(group_hsl.get(g, ORPHAN_HSL), float(c)) for g, c in group_counts.items()]
            hsl = blend_hsl(pairs)

        hsl_map[nid] = hsl
        color_map[nid] = hsl_to_hex(*hsl)
        cluster_map[nid] = group_cluster.get(own_group, "other")

    # Pass 2: orphan nodes (Rule 3)
    for node in nodes:
        nid = node["id"]
        if nid in color_map:
            continue

        soft_out = [e for e in edges_by_source.get(nid, []) if e["type"] == "soft"]
        pairs = []
        for e in soft_out:
            tgt_hsl = hsl_map.get(e["target"])
            if tgt_hsl is not None:
                pairs.append((tgt_hsl, float(e.get("weight", 0.1))))

        hsl = blend_hsl(pairs) if pairs else ORPHAN_HSL
        hsl_map[nid] = hsl
        color_map[nid] = hsl_to_hex(*hsl)
        cluster_map[nid] = ORPHAN_CLUSTER

    return [
        {
            **node,
            "color": color_map.get(node["id"], hsl_to_hex(*ORPHAN_HSL)),
            "meta_cluster": cluster_map.get(node["id"], ORPHAN_CLUSTER),
        }
        for node in nodes
    ]


def merge_layout(
    nodes: list[dict],
    layout: dict[str, dict],
) -> list[dict]:
    """Copy x/y from layout.json into each node.  Missing entries get x=y=0."""
    return [
        {**node, "x": layout.get(node["id"], {}).get("x", 0.0),
                 "y": layout.get(node["id"], {}).get("y", 0.0)}
        for node in nodes
    ]


def build_meta_taxonomy(
    group_hsl: dict[int, tuple[float, float, float]] | None = None,
    group_cluster: dict[int, str] | None = None,
) -> dict:
    """
    Build data/_global/meta-taxonomy.json content.
    Maps FNA main_group int → {cluster, color} for the frontend.
    """
    if group_hsl is None:
        group_hsl = MAIN_GROUP_HSL
    if group_cluster is None:
        group_cluster = MAIN_GROUP_CLUSTER

    return {
        "FNA": {
            str(g): {
                "cluster": group_cluster.get(g, "other"),
                "color": hsl_to_hex(*hsl),
            }
            for g, hsl in group_hsl.items()
        }
    }
