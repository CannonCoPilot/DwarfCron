"""Tests for chronicler.ingest.xml_parser — XML parsing logic.

Uses in-memory XML fixtures. No database required.
"""

import json
import xml.etree.ElementTree as ET

import pytest

from chronicler.ingest.xml_parser import (
    _parse_historical_figures,
    _parse_events,
    _parse_event_collections,
    _parse_regions,
    _parse_underground_regions,
    _parse_sites,
    _parse_entities,
    _parse_artifacts,
    _parse_written_contents,
    _parse_historical_eras,
    _parse_legends_plus,
    _int_or_none,
    _text,
    _int,
    _bool_flag,
)


WORLD_ID = 99


# ── Helpers ──────────────────────────────────────────────────────────────────

def _xml(s: str) -> ET.Element:
    """Parse an XML string into an Element."""
    return ET.fromstring(f"<root>{s}</root>")


# ── Boolean flag detection ──────────────────────────────────────────────────

class TestBooleanFlags:
    """Verify supernatural detection from XML structure (not tags)."""

    DEITY_XML = """
    <historical_figure>
        <id>1</id><name>Armok</name><race>DEITY</race>
        <sphere>war</sphere><sphere>fire</sphere>
        <birth_year>-1</birth_year>
    </historical_figure>
    """

    VAMPIRE_XML = """
    <historical_figure>
        <id>2</id><name>Stukos</name><race>DWARF</race>
        <active_interaction>DEITY_MAJOR_CURSE_VAMPIRISM</active_interaction>
        <birth_year>100</birth_year><death_year>-1</death_year>
    </historical_figure>
    """

    NECROMANCER_XML = """
    <historical_figure>
        <id>3</id><name>Ozud</name><race>HUMAN</race>
        <interaction_knowledge>SECRET_LIFE_AND_DEATH</interaction_knowledge>
    </historical_figure>
    """

    WEREBEAST_XML = """
    <historical_figure>
        <id>4</id><name>Kogan</name><race>DWARF</race>
        <active_interaction>DEITY_CURSE_WEREBEAST_WOLF</active_interaction>
    </historical_figure>
    """

    NORMAL_XML = """
    <historical_figure>
        <id>5</id><name>Urist</name><race>DWARF</race>
        <caste>FEMALE</caste><sex>0</sex>
        <birth_year>50</birth_year><death_year>120</death_year>
        <death_cause>old age</death_cause>
    </historical_figure>
    """

    def test_deity_detected(self):
        root = _xml(self.DEITY_XML)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        assert len(hfs) == 1
        hf = hfs[0]
        # Tuple indices: 12=is_deity, 13=is_force, 14=is_vampire,
        # 15=is_necromancer, 16=is_werebeast, 17=is_ghost
        # 20=spheres, 21=goals, 22=skills, 23=holds_artifact,
        # 24=active_interactions, 25=details
        assert hf[12] is True, "is_deity should be True"
        assert hf[14] is False, "is_vampire should be False"
        # Spheres should be in first-class TEXT[] column (index 20)
        spheres = hf[20]
        assert spheres is not None, "spheres should not be None for deity"
        assert "war" in spheres
        assert "fire" in spheres

    def test_vampire_detected(self):
        root = _xml(self.VAMPIRE_XML)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        assert hf[14] is True, "is_vampire should be True"
        assert hf[12] is False, "is_deity should be False"

    def test_necromancer_detected(self):
        root = _xml(self.NECROMANCER_XML)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        assert hf[15] is True, "is_necromancer should be True"

    def test_werebeast_detected(self):
        root = _xml(self.WEREBEAST_XML)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        assert hf[16] is True, "is_werebeast should be True"

    def test_normal_figure_no_flags(self):
        root = _xml(self.NORMAL_XML)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        assert hf[12] is False  # is_deity
        assert hf[14] is False  # is_vampire
        assert hf[15] is False  # is_necromancer
        assert hf[16] is False  # is_werebeast


# ── Event field mapping ─────────────────────────────────────────────────────

class TestEventFieldMapping:
    """Verify event XML fields map to correct CDM columns."""

    def test_hf_died_event(self):
        xml = """
        <historical_event>
            <id>100</id><year>253</year><seconds72>5000</seconds72>
            <type>hf died</type>
            <hfid>10</hfid>
            <slayer_hfid>20</slayer_hfid>
            <site_id>5</site_id>
        </historical_event>
        """
        root = _xml(xml)
        rows = _parse_events(root, WORLD_ID)
        assert len(rows) == 1
        # Tuple: (id, world_id, year, seconds, event_type,
        #         hf1, hf2, site, region, ent1, ent2, artifact, structure, details)
        row = rows[0]
        assert row[0] == 100  # id
        assert row[1] == WORLD_ID  # world_id
        assert row[2] == 253  # year
        assert row[4] == "hf died"  # event_type
        assert row[5] == 10  # hf_id_1 (victim)
        assert row[6] == 20  # hf_id_2 (slayer)
        assert row[7] == 5   # site_id

    def test_unmapped_fields_go_to_details(self):
        xml = """
        <historical_event>
            <id>200</id><year>100</year><type>artifact created</type>
            <hfid>30</hfid><artifact_id>7</artifact_id>
            <custom_field>custom_value</custom_field>
        </historical_event>
        """
        root = _xml(xml)
        rows = _parse_events(root, WORLD_ID)
        row = rows[0]
        assert row[5] == 30  # hf_id_1
        assert row[11] == 7  # artifact_id
        details = json.loads(row[13])
        assert details["custom_field"] == "custom_value"

    def test_skip_values_produce_none(self):
        xml = """
        <historical_event>
            <id>300</id><year>50</year><type>change hf state</type>
            <hfid>40</hfid><site_id>-1</site_id><region_id></region_id>
        </historical_event>
        """
        root = _xml(xml)
        rows = _parse_events(root, WORLD_ID)
        row = rows[0]
        assert row[5] == 40  # hf_id_1
        assert row[7] is None  # site_id = -1 → None
        assert row[8] is None  # region_id = "" → None


# ── Composite PK tuple structure ─────────────────────────────────────────────

class TestCompositePKs:
    """Verify all parsed tuples include world_id in correct position."""

    def test_hf_tuple_has_world_id(self):
        xml = '<historical_figure><id>1</id><name>Test</name></historical_figure>'
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        assert hfs[0][0] == 1        # id
        assert hfs[0][1] == WORLD_ID  # world_id

    def test_event_tuple_has_world_id(self):
        xml = '<historical_event><id>1</id><year>1</year><type>test</type></historical_event>'
        root = _xml(xml)
        rows = _parse_events(root, WORLD_ID)
        assert rows[0][0] == 1        # id
        assert rows[0][1] == WORLD_ID  # world_id

    def test_region_tuple_has_world_id(self):
        xml = '<regions><region><id>1</id><name>Test</name><type>Forest</type></region></regions>'
        root = _xml(xml)
        rows = _parse_regions(root, WORLD_ID)
        assert rows[0][0] == 1        # id
        assert rows[0][1] == WORLD_ID  # world_id

    def test_entity_tuple_has_world_id(self):
        xml = '<entities><entity><id>1</id><name>Test Civ</name><type>civilization</type></entity></entities>'
        root = _xml(xml)
        rows = _parse_entities(root, WORLD_ID)
        assert rows[0][0] == 1        # id
        assert rows[0][1] == WORLD_ID  # world_id

    def test_hf_link_tuple_has_world_id(self):
        xml = """
        <historical_figure><id>1</id><name>A</name>
            <hf_link><hfid>2</hfid><link_type>spouse</link_type></hf_link>
        </historical_figure>
        """
        root = _xml(xml)
        _, links, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        assert links[0][0] == WORLD_ID  # world_id
        assert links[0][1] == 1         # hf_id
        assert links[0][2] == 2         # target_hf_id

    def test_collection_tuple_has_world_id(self):
        xml = """
        <historical_event_collection>
            <id>1</id><type>war</type><name>Test War</name>
            <start_year>100</start_year><end_year>200</end_year>
        </historical_event_collection>
        """
        root = _xml(xml)
        colls, _, _ = _parse_event_collections(root, WORLD_ID)
        assert colls[0][0] == 1        # id
        assert colls[0][1] == WORLD_ID  # world_id


# ── Written contents parsing ─────────────────────────────────────────────────

class TestWrittenContents:

    def test_basic_parsing(self):
        xml = """
        <written_contents>
            <written_content>
                <id>0</id><title>The Fragile Coven</title>
                <author_hfid>312</author_hfid><author_roll>19</author_roll>
                <form>musical composition</form><form_id>43</form_id>
            </written_content>
        </written_contents>
        """
        root = _xml(xml)
        rows = _parse_written_contents(root, WORLD_ID)
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == 0           # id
        assert row[1] == WORLD_ID    # world_id
        assert row[2] == "The Fragile Coven"  # title
        assert row[3] == 312         # author_hf_id
        assert row[4] == "musical composition"  # form

    def test_styles_collected(self):
        xml = """
        <written_contents>
            <written_content>
                <id>1</id><title>My Poem</title>
                <author_hfid>1</author_hfid><form>poem</form>
                <style>melancholy:4</style><style>compassionate:1</style>
            </written_content>
        </written_contents>
        """
        root = _xml(xml)
        rows = _parse_written_contents(root, WORLD_ID)
        assert rows[0][8] == ["melancholy:4", "compassionate:1"]

    def test_no_written_contents_section(self):
        root = _xml("<other>stuff</other>")
        rows = _parse_written_contents(root, WORLD_ID)
        assert rows == []


# ── Historical eras parsing ──────────────────────────────────────────────────

class TestHistoricalEras:

    def test_age_of_myth(self):
        xml = """
        <historical_eras>
            <historical_era>
                <name>Age of Myth</name><start_year>-1</start_year>
            </historical_era>
        </historical_eras>
        """
        root = _xml(xml)
        rows = _parse_historical_eras(root, WORLD_ID)
        assert len(rows) == 1
        assert rows[0] == (WORLD_ID, "Age of Myth", -1)

    def test_start_year_minus_one_preserved(self):
        """Regression: start_year=-1 must NOT be skipped as a null value."""
        xml = """
        <historical_eras>
            <historical_era>
                <name>Test Era</name><start_year>-1</start_year>
            </historical_era>
        </historical_eras>
        """
        root = _xml(xml)
        rows = _parse_historical_eras(root, WORLD_ID)
        assert rows[0][2] == -1, "start_year=-1 must be preserved, not treated as None"

    def test_no_eras_section(self):
        root = _xml("<other>stuff</other>")
        rows = _parse_historical_eras(root, WORLD_ID)
        assert rows == []


# ── Underground regions parsing ──────────────────────────────────────────────

class TestUndergroundRegions:

    def test_type_and_depth_parsed(self):
        xml = """
        <underground_regions>
            <underground_region>
                <id>0</id><type>cavern</type><depth>1</depth>
            </underground_region>
            <underground_region>
                <id>1</id><type>magma sea</type><depth>3</depth>
            </underground_region>
        </underground_regions>
        """
        root = _xml(xml)
        rows = _parse_underground_regions(root, WORLD_ID)
        assert len(rows) == 2
        assert rows[0][0] == 0           # id
        assert rows[0][1] == WORLD_ID    # world_id
        assert rows[0][2] == "cavern"    # type
        assert rows[0][3] == 1           # depth
        assert rows[1][2] == "magma sea"
        assert rows[1][3] == 3


# ── Helper functions ─────────────────────────────────────────────────────────

class TestHelpers:

    def test_int_or_none_skip_values(self):
        assert _int_or_none("-1") is None
        assert _int_or_none("") is None
        assert _int_or_none("-1,-1") is None
        assert _int_or_none(None) is None

    def test_int_or_none_valid(self):
        assert _int_or_none("42") == 42
        assert _int_or_none("0") == 0

    def test_int_or_none_invalid(self):
        assert _int_or_none("abc") is None

    def test_text_returns_none_for_missing(self):
        root = ET.fromstring("<a><b>hello</b></a>")
        assert _text(root, "b") == "hello"
        assert _text(root, "c") is None

    def test_bool_flag_presence(self):
        root = ET.fromstring("<a><exists/></a>")
        assert _bool_flag(root, "exists") is True
        assert _bool_flag(root, "missing") is False
