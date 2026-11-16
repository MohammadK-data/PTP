import duckdb, json
con = duckdb.connect(); con.execute("SET threads=8")
O = "output/"; AG = "Data/2026 Agent Export as of 2026-10-26 CSV/"
def q(sql): return con.execute(sql).fetchall()
def csv(p): return f"read_csv('{p}', all_varchar=true, delim=',', quote='\"', escape='\"', max_line_size=20000000, header=true)"
F = {}
for s, d in [("p26", "2026-03-28"), ("s26", "2026-10-15")]:
    con.execute(f"CREATE TABLE {s}_info AS SELECT prop_id, py_owner_id, sup_num, prop_type_cd, market_value, arb_protest_flag, ca_agent_id, arb_agent_id, geo_id, deed_dt, hs_exempt, situs_city FROM {csv(O+d+'_2026_APPRAISAL_INFO.csv.gz')}")
    F[s+"-info"] = q(f"""select count(*), count(distinct prop_id), count(*) filter (where market_value::bigint=100), count(*) filter (where arb_protest_flag='T'),
        count(*) filter (where ca_agent_id::bigint<>0), count(*) filter (where arb_agent_id::bigint<>0), count(*) filter (where hs_exempt='T'),
        min(deed_dt), max(deed_dt), min(try_strptime(deed_dt,'%m%d%Y')), max(try_strptime(deed_dt,'%m%d%Y')) from {s}_info""")[0]
    F[s+"-sup"] = q(f"select sup_num::int, count(*) from {s}_info group by 1 order by 2 desc limit 6")
    F[s+"-ptype"] = q(f"select prop_type_cd, count(*) from {s}_info group by 1 order by 2 desc")
    F[s+"-agentjoin"] = q(f"select count(*) filter (where a.agent_id is null) from (select distinct ca_agent_id id from {s}_info where ca_agent_id::bigint<>0 union select distinct arb_agent_id from {s}_info where arb_agent_id::bigint<>0) x left join {csv(O+d+'_2026_APPRAISAL_AGENT.csv.gz')} a on a.agent_id=x.id")
    F[s+"-ent"] = q(f"select count(*), count(distinct prop_id), max(n) from (select prop_id, count(*) n from read_csv('{O+d}_2026_APPRAISAL_ENTITY_INFO.csv.gz', all_varchar=true, header=true) group by 1)")
    F[s+"-land"] = q(f"select count(distinct prop_id) from {csv(O+d+'_2026_APPRAISAL_LAND_DETAIL.csv.gz')}")
    F[s+"-impr"] = q(f"select count(distinct prop_id) from {csv(O+d+'_2026_APPRAISAL_IMPROVEMENT_INFO.csv.gz')}")
    F[s+"-arb"] = q(f"select prop_val_yr, arb_status, count(*) from {csv(O+d+'_2026_APPRAISAL_ARB.csv.gz')} group by all order by 3 desc limit 8")
    F[s+"-law"] = q(f"select min(prop_val_yr), max(prop_val_yr), count(distinct prop_id) from {csv(O+d+'_2026_APPRAISAL_LAWSUIT.csv.gz')}")
# snapshot comparison
F["changed"] = q("""select count(*) filter (where p.market_value<>s.market_value), count(*) filter (where p.prop_id is null), count(*) filter (where s.prop_id is null)
  from p26_info p full join s26_info s on p.prop_id=s.prop_id and p.py_owner_id=s.py_owner_id""")
# agent export joins
con.execute(f"CREATE TABLE pd AS SELECT \"Property ID\" pid, \"Year\" yr FROM {csv(AG+'FID_PropDataExport.csv')}")
F["pd"] = q("select count(*), count(distinct pid), min(yr), max(yr), count(*) filter (where pid::bigint::varchar not in (select prop_id::bigint::varchar from s26_info)) from pd")
for f, idc, yc in [("FID_ARBExport.csv", "Property ID", "Year"), ("FID_ProtesterExport.csv", "Property ID", "Year"), ("FID_ARBInquiryExport.csv", "Prop_id", "Prop_val_yr"),
                   ("FID_SalesImprovementExport.csv", "Property ID", "Year"), ("FID_EventsExport.csv", "Property ID", "Event Year"), ("FID_ARBLetterHistory.csv", "Property ID", "Year")]:
    F[f] = q(f"select \"{yc}\" y, count(*) from {csv(AG+f)} group by 1 order by 1 desc limit 6") + q(f"select count(*) filter (where \"{yc}\"::int=0), min(\"{yc}\"::int) filter (where \"{yc}\"::int>0) from {csv(AG+f)}")
F["arb26"] = q(f"select \"Protest Status\", count(*) from {csv(AG+'FID_ARBExport.csv')} where \"Year\"='2026' group by 1 order by 2 desc limit 8")
F["arbcases"] = q(f"select count(*), count(distinct (\"Property ID\", \"Year\", \"Case ID\")) from {csv(AG+'FID_ARBExport.csv')}")
F["sales"] = q(f"select count(*), count(distinct \"Sale ID\"), count(*) filter (where \"Sale Price\"::bigint>0), min(try_strptime(\"Sale Date\",'%m/%d/%Y')), max(try_strptime(\"Sale Date\",'%m/%d/%Y')) from {csv(AG+'FID_SalesExport.csv')}")
F["sales_yr"] = q(f"select year(try_strptime(\"Sale Date\",'%m/%d/%Y')) y, count(*) filter (where \"Sale Price\"::bigint>0), count(*) from {csv(AG+'FID_SalesExport.csv')} group by 1 order by 1 desc limit 5")
F["notice"] = q(f"select \"Notice_yr\", count(*), count(distinct \"Prop_id\") from {csv(AG+'FID_ApprNoticeExport.csv')} group by 1")
F["impr"] = q(f"select \"Year\", count(*), count(distinct \"Property ID\") from {csv(AG+'FID_ImprovementExport.csv')} group by 1")
F["land"] = q(f"select \"Year\", count(*), count(distinct \"Property ID\") from {csv(AG+'FID_LandExport.csv')} group by 1")
F["permit"] = q(f"select year(try_strptime(\"Issue Date\",'%m/%d/%Y')) y, count(*) from {csv(AG+'FID_BuildingPermitExport.csv')} group by 1 order by 1 desc limit 4")
F["prot_neg"] = q(f"select count(*) from {csv(AG+'FID_ProtesterExport.csv')} where \"Property ID\"::bigint<0")
F["ptype"] = q(f"select \"Protest by Type\", count(*) from {csv(AG+'FID_ProtesterExport.csv')} where \"Year\"='2026' group by 1 order by 2 desc limit 5")
F["income"] = q(f"select count(*), count(distinct \"Property ID\"), count(*) filter (where \"Comment\" like 'CONFIDENTIAL%') from {csv(AG+'FID_IncomeExport.csv')}")
# property summary
for k, p in [("ps26a", O+"2026 Property Summary Export as of 2026-03-28__1st Notice Run Preliminary (with header).csv"),
             ("ps26s", "Data/2026 Property Summary Export as of 2026-10-08_Sup 298/2026 Property Summary Export as of 2026-10-13_Sup 298.csv")]:
    con.execute(f"CREATE TABLE {k} AS SELECT * FROM {csv(p)}")
    cols = [r[0] for r in q(f"describe {k}")]
    pid = cols[0]
    F[k] = q(f"""select count(*), count(distinct "{pid}"), count(*) filter (where "Market_val"='null' or "Market_val" is null), count(*) filter (where try_cast("Market_val" as bigint) is null),
      count(*) filter (where "Geo_id" like '"%'), count(*) filter (where try_cast("{pid}" as bigint) is null) from {k}""") + [pid]
    F[k+"-join"] = q(f"""select count(*) filter (where s.prop_id is null) from (select distinct "{pid}" pid from {k} where try_cast("{pid}" as bigint) is not null) x
       left join (select distinct prop_id::bigint p, prop_id from s26_info) s on s.p = x.pid::bigint""")
    F[k+"-null"] = q(f"""select "Market_val", count(*) from {k} where try_cast("Market_val" as bigint) is null group by 1 limit 3""")
json.dump(F, open("profile/facts.json", "w"), default=str, indent=0)
for k, v in F.items(): print(k, v)
