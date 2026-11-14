## Read first: summary and caveats

**Coverage**

| County | 2026 | 2024–2025 | Four-group split |
|---|---|---|---|
| Dallas | complete | complete | all four groups, every year (protest archive 2022–2026) |
| Denton | complete | complete | all four groups, every year (CAD protest files 2022–2025) |
| Tarrant | complete | complete | all four groups 2025–2026; combined 2024 |
| Travis | complete | roll counts and homestead only | combined (no protest history before 2026) |
| Montgomery | complete | roll, homestead, agent of record | combined (no protest history before 2026) |
| Rockwall | complete (protests are a lower bound, see below) | roll, homestead, agent of record | combined |
| Hays | roll, homestead, agents (no protests) | roll counts and homestead | only seg_agent |
| Fort Bend | roll and homestead only | roll and homestead only | only homes_A |

**Not published by the CAD:** Fort Bend has no agent IDs and no protest file in any year. Hays has no protest file, and no agent field before 2026. Travis has no 2024–2025 certified export with agents or protests. Rockwall publishes no protest list. Its only per-account protest records are the ones still open on each export date, so its 2026 protest counts are a lower bound and 2024–2025 are blank.

**PTP agent IDs found** (where the prompt had none): Travis 1863738 (also 1328537, same name, no accounts). Tarrant 1487 (2025–2026); older agency code 00795 (2024). Denton 245 (also 718105, same name, no accounts). Montgomery 654513 (also 412 in the 2024 roll). Rockwall 1044073 (1044084 is marked "DO NOT USE"). The prompt's IDs were confirmed in each CAD's list: Dallas 306 and Hays A0180641. Fort Bend A0830173 could not be confirmed, because no Fort Bend file carries agent IDs. Travis IDs 1898343 (Camel) and 1898284 (Q-Solutions) are other firms with "Property Tax Protest" in the name and are **not** counted, even though `travis_values_2026_build.py` counts them. The same applies to Ballard, Smart Value and Camel elsewhere.

**PTP 2026 home protests vs. portal.** All are below the portal: Tarrant −5.8%, Rockwall −20%, Denton −17%, Montgomery −25%, Travis −61%. The CAD counts protests *filed under PTP's ID*. In Travis, of 2,556 homes ever appointed to PTP in 2026, 2,410 were protested, but only about 1,100 under PTP's ID. The rest were filed by another agent (mostly Ownwell, 792) or by the owner (513), and about 350 PTP appointments expire during 2026. Worth checking whether PTP files some protests as owner, or whether clients switched firms mid-season. Snapshot dates also matter: Denton's file is dated Jul 27 and Montgomery's Aug 4.

**Comptroller survey gaps over 5%**
- **Tarrant 2025 (+39% total, +15% agent-filed):** TAD's open-records file has 268,648 accounts with finalized 2025 cases, most settled by 41.47(g-1) joint motion. 2024 shows the same case pattern and matches the survey within 5%. So the 2025 gap looks like a difference in how TAD counted protests for the survey, not an extraction error.
- **Dallas (−6%):** exemption-only protests and 25.25 correction motions are excluded here. The survey probably counts them.
- **Tarrant 2024 agent-filed (−5.8%):** small.

**Rules adapted, in short**
- **"Has agent":** uses appointment dates (deadline May 15, or notice date + 30) only where they exist: the Travis, Denton and Montgomery agent-portal JSON. Elsewhere it is the agent on file in the roll (Dallas TAXPAYER_REP, PACS ca_agent_id, Hays AgentExport). TAD publishes no appointment list, so for Tarrant "has agent" means an agent is listed on a protest case that year, a lower bound.
- **Agent-filed vs owner-filed:** a home where both filed counts as agent-filed.
- **all_protests:** counts *cases* in Denton, Travis, Montgomery and Dallas. It counts *accounts* in Tarrant and Rockwall.
- **Firm grouping:** by brand name across counties. For example, all Ryan offices are Ryan LLC; the variant spellings of Elliott-Wellman, Goodrich, Five Stone and UPTG are merged. The per-county ID lists are in the notes below and in firm_share.csv `agent_ids`.

**Downloads made for this run:** Dallas ARB archive and 2024/2025 rolls. Denton 2025 certified JSON and 2022–2024 protest exports. Travis EARS 2024/2025. Montgomery 2024/2025 exports. Rockwall 2024/2025 exports. Fort Bend 2024/2025 certified exports. Hays 2024/2025 certified exports, fetched through the browser because Hays CAD blocks scripted downloads. Comptroller survey 2024/2025. Each raw download sits under `CAD Website/<County>/Data/*_download*/`.
