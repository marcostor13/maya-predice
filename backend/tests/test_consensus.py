"""Tests del motor de consenso multi-fuente (núcleo de veracidad)."""

from app.data.players.base import PlayerObservation, normalize_name
from app.models.squad import PlayerStatus, Position, SquadRole
from app.services.squad.consensus import build_player_consensus, merge_field


def test_normalize_name_strips_accents_and_punctuation():
    assert normalize_name("Vinícius Júnior") == "vinicius junior"
    assert normalize_name("Emiliano  Martínez") == "emiliano martinez"


def test_merge_field_majority_vote():
    cv = merge_field("position", [("a", "GK"), ("b", "GK"), ("c", "DEF")])
    assert cv.value == "GK"
    assert cv.reported_by == 3
    assert cv.agreement == 2 / 3
    assert cv.has_conflict is True
    assert cv.by_source == {"a": "GK", "b": "GK", "c": "DEF"}


def test_merge_field_ignores_none():
    cv = merge_field("club", [("a", "PSG"), ("b", None)])
    assert cv.value == "PSG"
    assert cv.reported_by == 1
    assert cv.has_conflict is False


def test_merge_field_tiebreak_by_priority():
    # Empate 1-1; gana la fuente con mayor prioridad (apifootball antes que wikidata).
    cv = merge_field(
        "shirt_number",
        [("wikidata", 9), ("apifootball", 10)],
        priority=("apifootball", "thesportsdb", "wikidata"),
    )
    assert cv.value == 10
    assert cv.has_conflict is True


def test_full_agreement_high_confidence():
    obs = [
        PlayerObservation("apifootball", "Lionel Messi", Position.FWD, 10, status=PlayerStatus.AVAILABLE),
        PlayerObservation("thesportsdb", "Lionel Messi", Position.FWD, 10, status=PlayerStatus.AVAILABLE),
        PlayerObservation("wikidata", "Lionel Messi", Position.FWD, 10, status=PlayerStatus.AVAILABLE),
    ]
    c = build_player_consensus(obs)
    assert c.full_name == "Lionel Messi"
    assert c.sources_count == 3
    assert c.confidence == 1.0
    assert c.conflicts == []
    assert c.value("position") == Position.FWD
    assert c.value("shirt_number") == 10


def test_conflict_lowers_confidence_and_is_flagged():
    obs = [
        PlayerObservation("apifootball", "Enzo Fernandez", Position.MID, 24, status=PlayerStatus.AVAILABLE),
        PlayerObservation("thesportsdb", "Enzo Fernandez", Position.MID, 24, status=PlayerStatus.DOUBTFUL),
        PlayerObservation("wikidata", "Enzo Fernandez", Position.MID, 8, status=PlayerStatus.AVAILABLE),
    ]
    c = build_player_consensus(obs)
    assert c.value("position") == Position.MID            # 3/3 de acuerdo
    assert c.value("shirt_number") == 24                  # 2/3 mayoría
    assert c.value("status") == PlayerStatus.AVAILABLE     # 2/3 mayoría
    assert c.confidence < 1.0
    conflict_fields = {cv.field for cv in c.conflicts}
    assert "shirt_number" in conflict_fields
    assert "status" in conflict_fields


def test_single_source_works():
    obs = [PlayerObservation("fixture", "Alisson", Position.GK, 1, role=SquadRole.STARTER)]
    c = build_player_consensus(obs)
    assert c.sources_count == 1
    assert c.value("role") == SquadRole.STARTER
    assert c.confidence == 1.0  # una sola fuente => acuerdo trivial
