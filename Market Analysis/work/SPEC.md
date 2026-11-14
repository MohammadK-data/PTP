# Per-county fragment spec (each county writes work/<county>/)

market.csv   one row per year, columns exactly:
county,year,total_accounts,accounts_cat_A,accounts_cat_B,accounts_cat_M,mineral_accounts,homes_A_homestead,homes_A_with_agent,homes_A_protested,homes_A_protested_by_agent,homes_A_protested_by_owner,homes_A_ptp_agent,homes_A_ptp_protested,all_protests,all_agent_protests,source_roll_file,source_agent_file,source_protest_file,roll_version_date

segments.csv one row per year, columns exactly:
county,year,homes_A,seg_agent,seg_owner_alone,seg_lapsed,seg_never,seg_lapsed_or_never,seg_ptp
  (fill either seg_lapsed+seg_never OR seg_lapsed_or_never; leave the other blank)
  seg_agent = has agent this year; seg_owner_alone = protested this year, no agent;
  seg_lapsed = protested in some year 2022..(year-1) but not this year, no agent now;
  seg_never = rest. seg_agent+seg_owner_alone+seg_lapsed+seg_never == homes_A.

firms.csv    one row per county/year/firm, columns exactly:
county,year,firm,agent_ids,homes_A_agent_of_record,homes_A_protests_filed,all_accounts_agent_of_rec
  rows: every firm with >=100 home (cat A) accounts as agent of record, "Property Tax Protest" always,
  "All other agents" (rest), "Owners (self-filed)" (homes_A_protests_filed = owner-filed home protests;
  agent_of_record columns blank). agent_ids = semicolon-separated IDs.

notes.md     source-log section for the county: exact URLs + file names, file dates, year(s),
  missing sources per year, PTP agent IDs found (and how), firm name -> IDs mapping (or the rule used),
  every rule adapted, caveats, sanity checks run.

Rules: county names "Dallas","Denton","Fort Bend","Hays","Montgomery","Rockwall","Tarrant","Travis".
Plain integers. Blank (empty) for not available — never estimate. Accounts = unique property IDs
(dedupe roll rows; Tarrant has dup rows per deed). total_accounts = all accounts in the roll incl. BPP/mineral.
Home = state code starts with "A" (use the account's primary/property state code; document which field).
mineral_accounts = state code G*/J*? -> NO: mineral = state code starting with "G" (oil/gas/minerals).
Homestead = HS (general residence homestead) for that year.
Has agent = active agent of record for that year: effective on/before the protest deadline
  (May 15 of the year, or noticeDt+30 if later) and not expired/revoked before it, when dates exist;
  if the source has only a current agent field (no dates), use it and say so in notes.md.
Protested = >=1 value protest that tax year (exclude clerical/correction/non-value appeal types; document).
Agent-filed = filer is an agent; owner-filed = owner. Count each home once per category
  (if both agent and owner filed, count as agent-filed). all_protests = protests (rows/cases) for all
  property types; document whether it counts cases or accounts. all_agent_protests likewise.
No owner names, addresses or account numbers in any output.
Scripts go in Market Analysis/etl/<county>_market.py (run with /Users/user2/PTP/.venv/bin/python -I).
