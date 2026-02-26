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

# ── HF expanded first-class columns ─────────────────────────────────────────

class TestHFExpandedFields:
    """Verify HF first-class columns: spheres, goals, skills, holds_artifact, active_interactions."""

    # HF tuple indices (26-field tuple):
    # 0=id, 1=world_id, 2=name, 3=race, 4=caste, 5=sex,
    # 6=birth_year, 7=birth_seconds72, 8=death_year, 9=death_seconds72,
    # 10=death_cause, 11=entity_id, 12=is_deity, 13=is_force, 14=is_vampire,
    # 15=is_necromancer, 16=is_werebeast, 17=is_ghost, 18=kill_count, 19=event_count,
    # 20=spheres, 21=goals, 22=skills, 23=holds_artifact, 24=active_interactions, 25=details

    def test_goals_parsed_to_json(self):
        xml = """
        <historical_figure>
            <id>10</id><name>Ambitioner</name><race>DWARF</race>
            <goal>IMMORTALITY</goal><goal>CRAFT_A_MASTERWORK</goal>
        </historical_figure>
        """
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        goals = json.loads(hf[21])
        assert goals == ["IMMORTALITY", "CRAFT_A_MASTERWORK"]

    def test_skills_parsed_to_json(self):
        xml = """
        <historical_figure>
            <id>11</id><name>Skilled</name><race>DWARF</race>
            <hf_skill><skill>MINING</skill><total_ip>5000</total_ip></hf_skill>
            <hf_skill><skill>MASONRY</skill><total_ip>1200</total_ip></hf_skill>
        </historical_figure>
        """
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        skills = json.loads(hf[22])
        assert len(skills) == 2
        assert skills[0]["name"] == "MINING"
        assert skills[0]["total_ip"] == 5000
        assert skills[1]["name"] == "MASONRY"

    def test_holds_artifact_parsed_to_list(self):
        xml = """
        <historical_figure>
            <id>12</id><name>Bearer</name><race>DWARF</race>
            <holds_artifact>100</holds_artifact>
            <holds_artifact>200</holds_artifact>
        </historical_figure>
        """
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        assert hf[23] == [100, 200]  # holds_artifact INTEGER[]

    def test_active_interactions_first_class(self):
        xml = """
        <historical_figure>
            <id>13</id><name>Cursed</name><race>DWARF</race>
            <active_interaction>DEITY_MAJOR_CURSE_VAMPIRISM</active_interaction>
            <active_interaction>DEITY_CURSE_WEREBEAST_WOLF</active_interaction>
        </historical_figure>
        """
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        interactions = hf[24]  # active_interactions TEXT[]
        assert "DEITY_MAJOR_CURSE_VAMPIRISM" in interactions
        assert "DEITY_CURSE_WEREBEAST_WOLF" in interactions

    def test_necromancer_knowledge_in_details(self):
        """interaction_knowledge should flow to details JSONB, not active_interactions."""
        xml = """
        <historical_figure>
            <id>14</id><name>Necro</name><race>HUMAN</race>
            <interaction_knowledge>SECRET_LIFE_AND_DEATH</interaction_knowledge>
        </historical_figure>
        """
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        details = json.loads(hf[25])
        assert "SECRET_LIFE_AND_DEATH" in details["interaction_knowledge"]

    def test_normal_hf_expanded_fields_none(self):
        """Normal HF with no special fields should have None for expanded columns."""
        xml = """
        <historical_figure>
            <id>15</id><name>Plain</name><race>DWARF</race>
        </historical_figure>
        """
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        hf = hfs[0]
        assert hf[20] is None  # spheres
        assert hf[21] is None  # goals
        assert hf[22] is None  # skills
        assert hf[23] is None  # holds_artifact (empty list → None)
        assert hf[24] is None  # active_interactions

    def test_hf_tuple_length_is_26(self):
        """Verify the expanded HF tuple is exactly 26 fields."""
        xml = '<historical_figure><id>1</id><name>T</name><race>D</race></historical_figure>'
        root = _xml(xml)
        hfs, _, _, _, _ = _parse_historical_figures(root, WORLD_ID)
        assert len(hfs[0]) == 26


# ── Sites parsing ───────────────────────────────────────────────────────────

class TestSitesParsing:
    """Verify site and structure parsing."""

    def test_basic_site_fields(self):
        xml = """
        <site>
            <id>1</id><name>Boatmurdered</name><type>fortress</type>
            <coords>50,75</coords>
        </site>
        """
        root = _xml(xml)
        sites, structs = _parse_sites(root, WORLD_ID)
        assert len(sites) == 1
        site = sites[0]
        assert site[0] == 1            # id
        assert site[1] == WORLD_ID     # world_id
        assert site[2] == "Boatmurdered"  # name
        assert site[3] == "fortress"   # type
        assert site[4] == 50           # coord_x
        assert site[5] == 75           # coord_y

    def test_site_with_structures(self):
        xml = """
        <site>
            <id>5</id><name>Rivercity</name><type>town</type><coords>10,20</coords>
            <structure>
                <local_id>0</local_id><name>Temple of Gold</name>
                <type>temple</type><entity_id>3</entity_id>
            </structure>
            <structure>
                <local_id>1</local_id><name>Market Square</name>
                <type>market</type>
            </structure>
        </site>
        """
        root = _xml(xml)
        sites, structs = _parse_sites(root, WORLD_ID)
        assert len(sites) == 1
        assert len(structs) == 2
        assert structs[0][0] == WORLD_ID  # world_id
        assert structs[0][1] == 5         # site_id
        assert structs[0][2] == 0         # local_id
        assert structs[0][3] == "Temple of Gold"
        assert structs[0][4] == "temple"
        assert structs[0][5] == 3         # entity_id

    def test_site_without_coords(self):
        xml = '<site><id>9</id><name>Lost</name><type>lair</type></site>'
        root = _xml(xml)
        sites, _ = _parse_sites(root, WORLD_ID)
        assert sites[0][4] is None  # coord_x
        assert sites[0][5] is None  # coord_y


# ── Artifacts parsing ───────────────────────────────────────────────────────

class TestArtifactsParsing:
    """Verify artifact parsing with alternative field names."""

    def test_basic_artifact(self):
        xml = """
        <artifact>
            <id>42</id><name>Thinwalls</name>
            <item_type>weapon</item_type><item_subtype>short sword</item_subtype>
            <mat>iron</mat><creator_hfid>100</creator_hfid>
            <holder_hfid>200</holder_hfid><site_id>5</site_id>
        </artifact>
        """
        root = _xml(xml)
        rows = _parse_artifacts(root, WORLD_ID)
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == 42        # id
        assert row[1] == WORLD_ID  # world_id
        assert row[2] == "Thinwalls"  # name
        assert row[3] == "weapon"  # item_type
        assert row[4] == "short sword"  # item_subtype
        assert row[5] == "iron"    # material
        assert row[6] == 100       # creator_hf_id
        assert row[7] == 200       # holder_hf_id
        assert row[8] == 5         # site_id

    def test_artifact_alt_field_names(self):
        """DF uses both name/name_string, item_type/item, mat/material."""
        xml = """
        <artifact>
            <id>43</id><name_string>Alt Name</name_string>
            <item>armor</item><material>steel</material>
            <hist_figure_id>150</hist_figure_id>
        </artifact>
        """
        root = _xml(xml)
        rows = _parse_artifacts(root, WORLD_ID)
        row = rows[0]
        assert row[2] == "Alt Name"  # name_string fallback
        assert row[3] == "armor"     # item fallback
        assert row[5] == "steel"     # material fallback
        assert row[6] == 150         # hist_figure_id fallback


# ── Entity parsing ──────────────────────────────────────────────────────────

class TestEntitiesParsing:
    """Verify entity parsing uses scoped path."""

    def test_basic_entity(self):
        xml = """
        <entities>
            <entity><id>1</id><name>The Hazy Realms</name><type>civilization</type><race>DWARF</race></entity>
            <entity><id>2</id><name>Goblin Empire</name><type>civilization</type><race>GOBLIN</race></entity>
        </entities>
        """
        root = _xml(xml)
        rows = _parse_entities(root, WORLD_ID)
        assert len(rows) == 2
        assert rows[0] == (1, WORLD_ID, "The Hazy Realms", "civilization", "DWARF", None)
        assert rows[1][2] == "Goblin Empire"

    def test_entities_scoped_path(self):
        """Entities inside events should NOT be picked up (scoped path prevents this)."""
        xml = """
        <entities>
            <entity><id>1</id><name>Real</name><type>civ</type></entity>
        </entities>
        <historical_event>
            <entity>999</entity>
        </historical_event>
        """
        root = _xml(xml)
        rows = _parse_entities(root, WORLD_ID)
        assert len(rows) == 1
        assert rows[0][0] == 1

    def test_entity_skip_missing_id(self):
        xml = '<entities><entity><name>NoID</name></entity></entities>'
        root = _xml(xml)
        rows = _parse_entities(root, WORLD_ID)
        assert rows == []


# ── Event collections ───────────────────────────────────────────────────────

class TestEventCollections:
    """Verify collection parsing with events and subcollections."""

    def test_war_collection(self):
        xml = """
        <historical_event_collection>
            <id>50</id><type>war</type><name>The War of Swords</name>
            <start_year>100</start_year><start_seconds72>0</start_seconds72>
            <end_year>200</end_year><end_seconds72>0</end_seconds72>
            <aggressor_ent_id>1</aggressor_ent_id>
            <defender_ent_id>2</defender_ent_id>
            <event>1000</event><event>1001</event><event>1002</event>
            <eventcol>51</eventcol><eventcol>52</eventcol>
        </historical_event_collection>
        """
        root = _xml(xml)
        colls, events, subs = _parse_event_collections(root, WORLD_ID)
        assert len(colls) == 1
        coll = colls[0]
        assert coll[0] == 50          # id
        assert coll[1] == WORLD_ID    # world_id
        assert coll[2] == "war"       # type
        assert coll[3] == "The War of Swords"  # name
        assert coll[5] == 100         # start_year
        assert coll[7] == 200         # end_year
        assert coll[9] == 1           # aggressor_ent_id
        assert coll[10] == 2          # defender_ent_id
        assert len(events) == 3
        assert events[0] == (WORLD_ID, 50, 1000)
        assert len(subs) == 2
        assert subs[0] == (WORLD_ID, 50, 51)

    def test_collection_skip_invalid_events(self):
        xml = """
        <historical_event_collection>
            <id>60</id><type>battle</type>
            <event>100</event><event>-1</event><event></event>
        </historical_event_collection>
        """
        root = _xml(xml)
        _, events, _ = _parse_event_collections(root, WORLD_ID)
        # -1 → None via _int_or_none, so skipped; empty text → skipped
        assert len(events) == 1
        assert events[0][2] == 100


# ── HF sub-links parsing ───────────────────────────────────────────────────

class TestHFSubLinks:
    """Verify entity_link, site_link, and position_link parsing."""

    def test_entity_links(self):
        xml = """
        <historical_figure>
            <id>20</id><name>Leader</name><race>DWARF</race>
            <entity_link>
                <entity_id>5</entity_id><link_type>member</link_type>
            </entity_link>
        </historical_figure>
        """
        root = _xml(xml)
        _, _, ent_links, _, _ = _parse_historical_figures(root, WORLD_ID)
        assert len(ent_links) == 1
        assert ent_links[0][0] == WORLD_ID  # world_id
        assert ent_links[0][1] == 20        # hf_id
        assert ent_links[0][2] == 5         # entity_id
        assert ent_links[0][3] == "member"  # link_type

    def test_site_links(self):
        xml = """
        <historical_figure>
            <id>21</id><name>Dweller</name><race>DWARF</race>
            <site_link>
                <site_id>10</site_id><link_type>home</link_type>
            </site_link>
        </historical_figure>
        """
        root = _xml(xml)
        _, _, _, site_links, _ = _parse_historical_figures(root, WORLD_ID)
        assert len(site_links) == 1
        assert site_links[0][2] == 10     # site_id
        assert site_links[0][3] == "home"

    def test_position_links_active_and_former(self):
        xml = """
        <historical_figure>
            <id>22</id><name>Noble</name><race>DWARF</race>
            <entity_position_link>
                <entity_id>1</entity_id><position_profile_id>3</position_profile_id>
                <start_year>150</start_year>
            </entity_position_link>
            <entity_former_position_link>
                <entity_id>1</entity_id><position_profile_id>2</position_profile_id>
                <start_year>100</start_year><end_year>149</end_year>
            </entity_former_position_link>
        </historical_figure>
        """
        root = _xml(xml)
        _, _, _, _, pos_links = _parse_historical_figures(root, WORLD_ID)
        assert len(pos_links) == 2
        # Active position: end_year = None
        assert pos_links[0][4] == 150     # start_year
        assert pos_links[0][5] is None    # end_year (still held)
        # Former position: has end_year
        assert pos_links[1][4] == 100     # start_year
        assert pos_links[1][5] == 149     # end_year


# ── Legends plus: art forms, rivers, mountain peaks, identities ─────────────

class TestLegendsPlus:
    """Test _parse_legends_plus with temp XML files."""

    LEGENDS_PLUS_TEMPLATE = """\
<?xml version="1.0" encoding="UTF-8"?>
<df_world>
    <name>Test World</name>
    <altname>The Realm of Testing</altname>
    {content}
</df_world>
"""

    def _write_plus(self, tmp_path, content: str) -> str:
        """Write legends_plus XML to a temp file, return path."""
        xml = self.LEGENDS_PLUS_TEMPLATE.format(content=content)
        fp = tmp_path / "test-legends_plus.xml"
        fp.write_text(xml, encoding="utf-8")
        return str(fp)

    def test_art_forms_three_types(self, tmp_path):
        content = """
        <dance_forms>
            <dance_form><id>0</id><name>The Twirl of Ages</name><description>A spinning dance</description></dance_form>
        </dance_forms>
        <musical_forms>
            <musical_form><id>0</id><name>Song of Hammers</name></musical_form>
        </musical_forms>
        <poetic_forms>
            <poetic_form><id>0</id><name>Ode to Magma</name><description>A poem about lava</description></poetic_form>
        </poetic_forms>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        arts = result["art_forms"]
        assert len(arts) == 3
        # Dance: (id, world_id, name, form_type, description, details)
        assert arts[0][0] == 0
        assert arts[0][1] == WORLD_ID
        assert arts[0][2] == "The Twirl of Ages"
        assert arts[0][3] == "dance"
        assert arts[0][4] == "A spinning dance"
        # Musical: no description
        assert arts[1][3] == "musical"
        assert arts[1][4] is None
        # Poetic
        assert arts[2][3] == "poetic"
        assert arts[2][2] == "Ode to Magma"

    def test_art_form_extra_fields_in_details(self, tmp_path):
        content = """
        <dance_forms>
            <dance_form>
                <id>5</id><name>Stomp</name>
                <custom_prop>fast_tempo</custom_prop>
            </dance_form>
        </dance_forms>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        details = json.loads(result["art_forms"][0][5])
        assert details["custom_prop"] == "fast_tempo"

    def test_rivers_synthetic_ids(self, tmp_path):
        content = """
        <rivers>
            <river><name>Oilwhisker</name><name_english>The River of Flames</name_english><path>50:75|51:75</path></river>
            <river><name>Clearwater</name></river>
            <river><name>Muddymire</name></river>
        </rivers>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        rivers = result["rivers"]
        assert len(rivers) == 3
        # Synthetic IDs: 0, 1, 2
        assert rivers[0][0] == 0
        assert rivers[1][0] == 1
        assert rivers[2][0] == 2
        # First river fields
        assert rivers[0][1] == WORLD_ID
        assert rivers[0][2] == "Oilwhisker"
        assert rivers[0][3] == "The River of Flames"  # name_english
        assert rivers[0][4] == "50:75|51:75"  # path

    def test_mountain_peaks_is_volcano(self, tmp_path):
        content = """
        <mountain_peaks>
            <mountain_peak>
                <id>0</id><name>Mount Doom</name><coords>10,20</coords>
                <height>400</height><is_volcano/>
            </mountain_peak>
            <mountain_peak>
                <id>1</id><name>Gentle Hill</name><coords>30,40</coords>
                <height>150</height>
            </mountain_peak>
        </mountain_peaks>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        peaks = result["mountain_peaks"]
        assert len(peaks) == 2
        # Tuple: (id, world_id, name, coords, height, is_volcano)
        assert peaks[0][0] == 0
        assert peaks[0][2] == "Mount Doom"
        assert peaks[0][4] == 400
        assert peaks[0][5] is True   # is_volcano (presence tag)
        assert peaks[1][5] is False  # no is_volcano tag

    def test_identities_extended_fields(self, tmp_path):
        content = """
        <identities>
            <identity>
                <id>7</id><name>Shadow Walker</name>
                <histfig_id>100</histfig_id><birth_year>200</birth_year>
                <entity_id>3</entity_id>
                <race>HUMAN</race><caste>MALE</caste><profession>thief</profession>
            </identity>
        </identities>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        idents = result["identities"]
        assert len(idents) == 1
        # Tuple: (id, world_id, name, histfig_id, birth_year, birth_second, entity_id,
        #         race, caste, profession)
        ident = idents[0]
        assert ident[0] == 7
        assert ident[1] == WORLD_ID
        assert ident[2] == "Shadow Walker"
        assert ident[3] == 100       # histfig_id
        assert ident[6] == 3         # entity_id
        assert ident[7] == "HUMAN"   # race
        assert ident[8] == "MALE"    # caste
        assert ident[9] == "thief"   # profession

    def test_world_name_extracted(self, tmp_path):
        fp = self._write_plus(tmp_path, "")
        result = _parse_legends_plus(fp, WORLD_ID)
        assert result["world_name"] == "Test World"
        assert result["world_alt_name"] == "The Realm of Testing"

    def test_entity_populations_parsed(self, tmp_path):
        content = """
        <entity_populations>
            <entity_population>
                <id>0</id><race>DWARF:5000</race><civ_id>1</civ_id>
            </entity_population>
            <entity_population>
                <id>1</id><race>goblin:1200</race><civ_id>2</civ_id>
            </entity_population>
            <entity_population>
                <id>2</id><race>elf</race><civ_id>3</civ_id>
            </entity_population>
        </entity_populations>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        pops = result["entity_populations"]
        assert len(pops) == 3
        # Tuple: (id, world_id, race, count, civ_id)
        assert pops[0][0] == 0
        assert pops[0][1] == WORLD_ID
        assert pops[0][2] == "DWARF"     # race (split from "DWARF:5000")
        assert pops[0][3] == 5000        # count
        assert pops[0][4] == 1           # civ_id
        assert pops[1][2] == "goblin"    # lowercase preserved
        assert pops[1][3] == 1200
        assert pops[2][2] == "elf"       # no count in race string
        assert pops[2][3] is None        # no count available

    def test_empty_sections_produce_empty_lists(self, tmp_path):
        fp = self._write_plus(tmp_path, "")
        result = _parse_legends_plus(fp, WORLD_ID)
        assert result["art_forms"] == []
        assert result["rivers"] == []
        assert result["entity_populations"] == []
        assert result["hf_enrichment"] == []

    def test_entity_positions_parsed(self, tmp_path):
        content = """
        <entities>
            <entity>
                <id>1</id><name>The Hazy Realms</name><type>civilization</type>
                <entity_position>
                    <id>0</id><name>king</name>
                    <name_male>King</name_male><name_female>Queen</name_female>
                </entity_position>
                <entity_position_assignment>
                    <histfig>500</histfig><position_id>0</position_id>
                </entity_position_assignment>
            </entity>
        </entities>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        positions = result["entity_positions"]
        assert len(positions) == 1
        assert positions[0][1] == 1        # entity_id
        assert positions[0][3] == "king"   # name
        assignments = result["entity_position_assignments"]
        assert len(assignments) == 1
        assert assignments[0][1] == 500    # histfig

    def test_event_relationships(self, tmp_path):
        content = """
        <historical_event_relationships>
            <historical_event_relationship>
                <event>1000</event>
                <relationship>mother</relationship>
                <source_hf>10</source_hf><target_hf>20</target_hf>
                <year>150</year>
            </historical_event_relationship>
        </historical_event_relationships>
        """
        fp = self._write_plus(tmp_path, content)
        result = _parse_legends_plus(fp, WORLD_ID)
        rels = result["event_relationships"]
        assert len(rels) == 1
        assert rels[0][0] == WORLD_ID
        assert rels[0][1] == 1000        # event_id
        assert rels[0][2] == "mother"    # relationship
        assert rels[0][3] == 10          # source_hf
        assert rels[0][4] == 20          # target_hf


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
