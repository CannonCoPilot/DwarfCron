<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/PostgreSQL-pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/AI-Embedding%20%2B%20LLM-blueviolet?style=for-the-badge" alt="AI"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT"/>
</p>

# Chronicler (DwarfCron)

**An AI-powered living atlas and narrative engine that transforms 7.6 million years of simulated history into browsable, cross-linked, AI-narrated chronicles.**

Chronicler connects to a running [Dwarf Fortress](https://www.bay12games.com/dwarves/) game via [DFHack](https://dfhack.org/), ingests its procedurally generated world data (XML legends exports + live in-game memory), maps it into a normalized relational schema, and serves a web UI for exploration, search, and AI-generated storytelling.

---

## What Makes This Technically Interesting

This isn't a game mod — it's a **full-stack data engineering pipeline** that demonstrates:

### 1. Complex Data Modeling (CDM)

The game generates deeply interconnected historical data: civilizations, wars, artifacts, family trees, geological layers, building construction, and millions of events spanning thousands of simulated years. Chronicler normalizes this into a **40+ table PostgreSQL schema** with:

- **Bidirectional relationship graphs** (parent-child, spouse, master-apprentice, killer-victim)
- **Temporal event chains** with knowledge-horizon filtering (what did this character *actually know*?)
- **Composite primary keys** across entity-event-relationship dimensions
- **14 ETL functions** that map raw XML/Protobuf into the CDM

```
XML Legends Export ──► Parser ──► CDM Schema ──► PostgreSQL
                                      │              │
Live DFHack Memory ──► Bridge ──► ETL Pipeline    pgvector
                                      │              │
                                 Scoring Engine   Embeddings
                                      │              │
                                 Narrative Layer  Semantic Search
```

### 2. Live Memory Streaming

DFHack exposes the game's in-memory data structures via Lua/Protobuf RPC. Chronicler's bridge module:

- **Captures fortress state snapshots** (206 snapshots, 563 events, 76 units in validation)
- **Streams unit status, building construction, combat events** in real-time
- **Maps C++ memory structs** (personality traits, beliefs, emotions from `unit.status.current_soul`) into normalized database rows
- **Handles schema evolution** across game versions without breaking live connections

### 3. AI-Driven Narrative Generation

Raw data becomes stories through a multi-stage pipeline:

- **Importance scoring**: 473K events scored for narrative significance using configurable weights
- **Arc detection**: 13K narrative arcs identified across character lifespans
- **Link synthesis**: 28K cross-references between entities, events, and locations
- **LLM generation**: Claude and local models produce character biographies, battle accounts, and civilization summaries
- **Embedding pipeline**: pgvector-powered semantic search across the entire generated corpus (2560-dim Qwen3 embeddings)

### 4. Web Explorer

A FastAPI + Jinja2 web application with 151 HTML templates providing:

- **World browser**: civilizations, sites, regions, underground layers
- **Entity explorer**: historical figures with family trees, life events, relationships
- **Artifact tracker**: creation, ownership chains, claim/transfer events
- **Battle reconstructor**: combat events with participants, casualties, tactical context
- **Calendar view**: seasonal event timelines across in-game years
- **Semantic search**: natural-language queries against the embedded corpus

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Dwarf Fortress                     │
│                  (UTM VM / Windows)                   │
│                        │                              │
│                   DFHack RPC                          │
└────────────────────────┼─────────────────────────────┘
                         │ SSH + Lua/Protobuf
┌────────────────────────┼─────────────────────────────┐
│                    Chronicler                          │
│                        │                              │
│  ┌─────────┐    ┌─────┴──────┐    ┌──────────────┐  │
│  │  Ingest  │    │   Bridge    │    │   Explorer    │  │
│  │  (XML)   │    │  (DFHack)   │    │  (FastAPI)    │  │
│  └────┬─────┘    └─────┬──────┘    └──────┬───────┘  │
│       │                │                   │          │
│  ┌────┴────────────────┴───────────────────┤          │
│  │           PostgreSQL + pgvector          │          │
│  │     40+ tables │ 14 ETL functions        │          │
│  │     CDM Schema │ Embedding index         │          │
│  └─────────────────────────────────────────┘          │
│                        │                              │
│  ┌─────────────────────┴───────────────────┐          │
│  │          Narrative Engine                │          │
│  │  Scoring → Arcs → Links → LLM Gen       │          │
│  └─────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────┘
```

---

## Data Scale

| Metric | Value |
|--------|-------|
| Simulated history | ~7,600 years |
| Historical figures | 50,000+ per world |
| Events | 500,000+ per world |
| Narrative arcs detected | 13,000+ |
| Cross-reference links | 28,000+ |
| Scored events | 473,000+ |
| Database tables | 40+ |
| ETL functions | 14 |
| SQL migrations | 18 |
| Web templates | 151 |
| Python modules | 1,626 files |

---

## Tech Stack

**Backend**: Python 3.11+, FastAPI, asyncpg, Click CLI  
**Database**: PostgreSQL with pgvector (2560-dim embeddings), 18 migration files  
**AI/ML**: Claude API, Qwen3 embeddings (MLX), narrative scoring algorithms  
**Game Integration**: DFHack Lua/Protobuf RPC over SSH, XML legends parsing (lxml)  
**Frontend**: Jinja2 templates, SSE for live updates  
**Infrastructure**: Docker, UTM (Windows VM for DF), tmux automation  

---

## Project Status

| Phase | Name | Status |
|-------|------|--------|
| 1 | Data Foundation | **Complete** (64/64 tasks) |
| 2 | Explorer Core | **Complete** (50/50 DoD) |
| 3 | Live Integration | **Complete** (27/27 DoD) |
| 4 | Narrative Engine | In Progress |
| 5 | Visualization | Planned |
| 6 | Advanced Components | Planned |
| 7 | Polish & Production | Planned |

---

## Quick Start

```bash
pip install -e .
chronicler serve --reload    # Web UI at http://localhost:8080
chronicler ingest world.xml  # Import a legends export
```

---

## License

MIT License

---

<p align="center">
  <em>Chronicler — because every dwarf's story deserves to be told.</em>
</p>
