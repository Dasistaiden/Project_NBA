from fetcher import map_positions

MAPPING = {
    "G": ["PG", "SG"], "F": ["SF", "PF"], "C": ["C"],
    "G-F": ["SG", "SF"], "F-G": ["SG", "SF"],
    "F-C": ["PF", "C"], "C-F": ["PF", "C"],
}


def test_all_known_positions():
    assert map_positions("G", MAPPING) == "PG,SG"
    assert map_positions("F", MAPPING) == "SF,PF"
    assert map_positions("C", MAPPING) == "C"
    assert map_positions("G-F", MAPPING) == "SG,SF"
    assert map_positions("F-C", MAPPING) == "PF,C"


def test_unknown_position_empty():
    assert map_positions("", MAPPING) == ""
    assert map_positions("XX", MAPPING) == ""
