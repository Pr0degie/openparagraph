import math

import pytest

from src.color_builder import (
    MAIN_GROUP_CLUSTER,
    MAIN_GROUP_HSL,
    ORPHAN_CLUSTER,
    ORPHAN_HSL,
    assign_colors,
    blend_hsl,
    build_meta_taxonomy,
    hsl_to_hex,
    merge_layout,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Minimal 4-node graph covering all three rules:
#  bgb:   group 4, references stgb (group 4) and hgb (group 5) → bridging
#  stgb:  group 4, references only bgb (group 4) → unambiguous
#  hgb:   group 5, no out-edges → unambiguous
#  orphan: no FNA, soft edge → bgb → Rule 3

def _node(nid, group):
    return {
        "id": nid,
        "classification": {"scheme": "FNA", "code": None, "main_group": group},
        "x": None, "y": None, "color": None, "meta_cluster": None,
    }

NODES = [
    _node("de-bund/BGB", 4),
    _node("de-bund/StGB", 4),
    _node("de-bund/HGB", 5),
    _node("de-bund/ORPHAN", None),
]

EDGES = [
    {"source": "de-bund/BGB",    "target": "de-bund/StGB",   "type": "explicit", "weight": 1.0},
    {"source": "de-bund/BGB",    "target": "de-bund/HGB",    "type": "explicit", "weight": 1.0},
    {"source": "de-bund/StGB",   "target": "de-bund/BGB",    "type": "explicit", "weight": 1.0},
    {"source": "de-bund/ORPHAN", "target": "de-bund/BGB",    "type": "soft",     "weight": 0.1},
]

LAYOUT = {
    "de-bund/BGB":    {"x": 10.0, "y": -5.0},
    "de-bund/StGB":   {"x": 20.0, "y":  3.0},
    "de-bund/HGB":    {"x": -8.0, "y":  1.0},
    "de-bund/ORPHAN": {"x":  0.0, "y":  0.0},
}


# ---------------------------------------------------------------------------
# hsl_to_hex
# ---------------------------------------------------------------------------


def test_hsl_to_hex_red():
    assert hsl_to_hex(0, 100, 50) == "#ff0000"


def test_hsl_to_hex_white():
    assert hsl_to_hex(0, 0, 100) == "#ffffff"


def test_hsl_to_hex_black():
    assert hsl_to_hex(0, 0, 0) == "#000000"


def test_hsl_to_hex_format():
    result = hsl_to_hex(200, 50, 50)
    assert result.startswith("#")
    assert len(result) == 7


# ---------------------------------------------------------------------------
# blend_hsl
# ---------------------------------------------------------------------------


def test_blend_hsl_single_color_unchanged():
    hsl = (100.0, 80.0, 50.0)
    result = blend_hsl([(hsl, 1.0)])
    assert abs(result[0] - 100.0) < 0.01
    assert abs(result[1] - 80.0) < 0.01
    assert abs(result[2] - 50.0) < 0.01


def test_blend_hsl_two_equal_weights():
    # H=0 and H=180, S=80, L=50 → expect H≈90 or 270 (both midpoints)
    # Actually 0° and 180° vectors cancel to (0,0), atan2(0,0)=0°
    # Let's use 0° and 90°
    h, s, l = blend_hsl([((0, 80, 50), 1.0), ((90, 80, 50), 1.0)])
    assert abs(h - 45.0) < 1.0
    assert abs(s - 80.0) < 0.01
    assert abs(l - 50.0) < 0.01


def test_blend_hsl_circular_hue_wraparound():
    # 350° and 10° → midpoint should be 0° (not 180°)
    h, s, l = blend_hsl([((350, 80, 50), 1.0), ((10, 80, 50), 1.0)])
    assert h < 20.0 or h > 340.0  # near 0°


def test_blend_hsl_empty_returns_orphan_hsl():
    result = blend_hsl([])
    assert result == ORPHAN_HSL


def test_blend_hsl_weighted():
    # 2× weight on hue=0, 1× weight on hue=90 → closer to 0
    h, _, _ = blend_hsl([((0, 80, 50), 2.0), ((90, 80, 50), 1.0)])
    # Weighted mean angle should be < 45°
    assert h < 45.0


# ---------------------------------------------------------------------------
# merge_layout
# ---------------------------------------------------------------------------


def test_merge_layout_sets_xy():
    updated = merge_layout(NODES, LAYOUT)
    bgb = next(n for n in updated if n["id"] == "de-bund/BGB")
    assert bgb["x"] == 10.0
    assert bgb["y"] == -5.0


def test_merge_layout_missing_node_defaults_to_zero():
    updated = merge_layout(NODES, {})
    for n in updated:
        assert n["x"] == 0.0
        assert n["y"] == 0.0


def test_merge_layout_does_not_mutate_input():
    original_x = NODES[0].get("x")
    merge_layout(NODES, LAYOUT)
    assert NODES[0].get("x") == original_x


# ---------------------------------------------------------------------------
# assign_colors — Rule 1 (unambiguous)
# ---------------------------------------------------------------------------


def test_assign_colors_unambiguous_uses_own_group_hue():
    nodes = assign_colors(NODES, EDGES)
    # HGB: group 5, no out-edges → pure group-5 color
    hgb = next(n for n in nodes if n["id"] == "de-bund/HGB")
    assert hgb["color"] == hsl_to_hex(*MAIN_GROUP_HSL[5])


def test_assign_colors_unambiguous_meta_cluster():
    nodes = assign_colors(NODES, EDGES)
    hgb = next(n for n in nodes if n["id"] == "de-bund/HGB")
    assert hgb["meta_cluster"] == MAIN_GROUP_CLUSTER[5]


def test_assign_colors_single_group_refs_is_unambiguous():
    # StGB only references BGB (also group 4) → unambiguous
    nodes = assign_colors(NODES, EDGES)
    stgb = next(n for n in nodes if n["id"] == "de-bund/StGB")
    assert stgb["color"] == hsl_to_hex(*MAIN_GROUP_HSL[4])


# ---------------------------------------------------------------------------
# assign_colors — Rule 2 (bridging)
# ---------------------------------------------------------------------------


def test_assign_colors_bridging_differs_from_pure_hue():
    # BGB references both group 4 (StGB) and group 5 (HGB) → bridging blend
    nodes = assign_colors(NODES, EDGES)
    bgb = next(n for n in nodes if n["id"] == "de-bund/BGB")
    pure_group4 = hsl_to_hex(*MAIN_GROUP_HSL[4])
    assert bgb["color"] != pure_group4  # blended, not pure


def test_assign_colors_bridging_meta_cluster_uses_own_group():
    nodes = assign_colors(NODES, EDGES)
    bgb = next(n for n in nodes if n["id"] == "de-bund/BGB")
    assert bgb["meta_cluster"] == MAIN_GROUP_CLUSTER[4]


# ---------------------------------------------------------------------------
# assign_colors — Rule 3 (orphan)
# ---------------------------------------------------------------------------


def test_assign_colors_orphan_meta_cluster():
    nodes = assign_colors(NODES, EDGES)
    orphan = next(n for n in nodes if n["id"] == "de-bund/ORPHAN")
    assert orphan["meta_cluster"] == ORPHAN_CLUSTER


def test_assign_colors_orphan_color_not_none():
    nodes = assign_colors(NODES, EDGES)
    orphan = next(n for n in nodes if n["id"] == "de-bund/ORPHAN")
    assert orphan["color"] is not None
    assert orphan["color"].startswith("#")


def test_assign_colors_isolated_orphan_gets_default_color():
    # orphan with no soft edges at all
    isolated = [_node("de-bund/ISO", None)]
    nodes = assign_colors(isolated, [])
    assert nodes[0]["color"] == hsl_to_hex(*ORPHAN_HSL)
    assert nodes[0]["meta_cluster"] == ORPHAN_CLUSTER


# ---------------------------------------------------------------------------
# assign_colors — general
# ---------------------------------------------------------------------------


def test_assign_colors_all_nodes_get_color():
    nodes = assign_colors(NODES, EDGES)
    for n in nodes:
        assert n["color"] is not None


def test_assign_colors_does_not_mutate_input():
    import copy
    original = copy.deepcopy(NODES)
    assign_colors(NODES, EDGES)
    for orig, current in zip(original, NODES):
        assert orig["color"] == current["color"]


def test_assign_colors_custom_palette():
    custom_hsl = {g: (0, 0, 50) for g in range(1, 10)}  # all gray
    custom_cluster = {g: "gray-group" for g in range(1, 10)}
    nodes = assign_colors(NODES, EDGES, group_hsl=custom_hsl, group_cluster=custom_cluster)
    hgb = next(n for n in nodes if n["id"] == "de-bund/HGB")
    assert hgb["color"] == hsl_to_hex(0, 0, 50)


# ---------------------------------------------------------------------------
# build_meta_taxonomy
# ---------------------------------------------------------------------------


def test_build_meta_taxonomy_has_fna_key():
    tax = build_meta_taxonomy()
    assert "FNA" in tax


def test_build_meta_taxonomy_has_nine_groups():
    tax = build_meta_taxonomy()
    assert len(tax["FNA"]) == 9


def test_build_meta_taxonomy_group_schema():
    tax = build_meta_taxonomy()
    for key, entry in tax["FNA"].items():
        assert "cluster" in entry
        assert "color" in entry
        assert entry["color"].startswith("#")


def test_build_meta_taxonomy_string_keys():
    tax = build_meta_taxonomy()
    for key in tax["FNA"]:
        assert isinstance(key, str)
