"""Fort Bend (FBCAD) commercial protest reductions, tax years 2025 and 2026.

reduction = value before protest (notice) - final value, counted only when > 0.

  notice value : first FBCAD *preliminary* Orion export holding the account
                 (2026: 2026-04-21, fallback 2026-06-15;
                  2025: 2025-04-01, fallback 2025-05-06).
                 Checked against our own client sheet: the April snapshot equals the
                 notice Market Value for 99.5% of 2025 FB clients and for every filled-in
                 2026 FB client row.
  final value  : latest roll = October 2026 Property Data Export
                 (CurrMarketValue for 2026, MarketValue = prior year for 2025). This
                 includes ARB results for protests still open at certification
                 (Sup 1-4). The certified Orion value is also reported (reduction_vs_cert).
                 Matches our client sheet Final Value for 99.0% of 2025 FB clients.
  market value : Orion OwnerExport ImpHS+ImpNHS+LandHS+LandNHS+AgMkt+TimMkt, summed over owners.
  commercial   : StateCodeLand or StateCodeImp in F1/F1H/F1M/F1X/F1V, F2, B1-B3 on that
                 year's certified roll (matches 04_Analysis counts 9,353 / 9,788).
  PTP client   : account listed for Fort Bend in the "2026 PTP Reductions" Google Sheet
                 (tabs 2026 and 2025), exported to client CSVs. FBCAD public files carry no
                 agent IDs, so A0830173 cannot be matched on the CAD side.

Caveats: FBCAD publishes no protest list, so any notice->final decrease counts as a
reduction, including the few that come from CAD corrections or account splits. Those are
flagged (geom_change = acreage shrank >5% or final = 0; legal_changed) and also reported
excluded.

Usage: python fort_bend_commercial_reductions.py CLIENTS_2026.csv CLIENTS_2025.csv OUT_DIR
"""
import glob
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

D = "/Users/user2/PTP/CAD Website/For Bend/Data"
ORION = {
    "O25_0401": f"{D}/fbcad_2025_preliminary_0401",
    "O25_0506": f"{D}/fbcad_2025_preliminary_0506",
    "C25": f"{D}/fbcad_2025_certified_download",
    "O26_0421": f"{D}/2026_04_21_0828-Orion-2026-Preliminary-Export-Redacted",
    "O26_0615": f"{D}/2026_06_15_1742-Orion-2026-Preliminary-Export-Redacted-2",
    "C26": f"{D}/2026_07_07_1746 Orion 2026 Certified Export-Redacted",
}
PDE_OCT26 = f"{D}/October2026-PropertyDataExport/October-Property Data Files/*.txt"
VAL = ["ImpHSValue", "ImpNHSValue", "LandHSValue", "LandNHSValue", "AgMktValue", "TimMktValue"]
COM = re.compile(r"^(F1[HMXV]?|F2|B[123])$")
CFG = {
    2026: dict(roll="C26", notice=["O26_0421", "O26_0615"], final="cur"),
    2025: dict(roll="C25", notice=["O25_0401", "O25_0506"], final="prior"),
}


def one(pattern):
    m = [p for p in glob.glob(pattern, recursive=True) if not p.endswith(".zip")]
    assert len(m) == 1, (pattern, m)
    return m[0]


def load_orion(key):
    base = glob.escape(ORION[key])
    p = pd.read_csv(one(f"{base}/**/*PropertyExport*"), dtype=str, encoding="utf-8-sig",
                    usecols=["PropertyQuickRefID", "StateCodeLand", "StateCodeImp",
                             "ARBProtestFlag", "Acres", "LegalDesc"])
    o = pd.read_csv(one(f"{base}/**/*OwnerExport*"), dtype=str, encoding="utf-8-sig",
                    usecols=["PropertyQuickRefID"] + VAL)
    o["mkt"] = o[VAL].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    v = o.groupby("PropertyQuickRefID")["mkt"].sum()
    return key, p.set_index("PropertyQuickRefID").join(v)


def load_pde(_):
    f = pd.read_csv(one(PDE_OCT26), dtype=str, encoding="utf-8-sig",
                    usecols=["QuickRefID", "CurrMarketValue", "MarketValue"])
    f = f.drop_duplicates("QuickRefID").set_index("QuickRefID")
    f = f.rename(columns={"CurrMarketValue": "cur", "MarketValue": "prior"}).apply(pd.to_numeric, errors="coerce")
    return "PDE", f


def clients(path, col):
    c = pd.read_csv(path, dtype=str)
    return set(c.loc[c["County"].str.contains("Bend", case=False, na=False), col].str.strip())


def main(c26, c25, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(load_orion, k) for k in ORION] + [ex.submit(load_pde, None)]
        S = dict(f.result() for f in futs)
    cl = {2026: clients(c26, "Account #"), 2025: clients(c25, "Account Number")}

    detail, rows = [], []
    for yr, c in CFG.items():
        r = S[c["roll"]]
        is_com = r.StateCodeLand.fillna("").str.match(COM) | r.StateCodeImp.fillna("").str.match(COM)
        df = r.loc[is_com, ["StateCodeLand", "StateCodeImp", "ARBProtestFlag", "Acres", "LegalDesc", "mkt"]]
        df = df.rename(columns={"mkt": "cert_value"})
        df["notice_value"], df["notice_src"] = float("nan"), None
        n_acres = pd.Series(float("nan"), index=df.index)
        n_legal = pd.Series("", index=df.index)
        for k in c["notice"]:
            snap = S[k]
            m = df.notice_value.isna() & df.index.isin(snap.index)
            df.loc[m, "notice_value"] = snap.mkt.reindex(df.index[m]).values
            df.loc[m, "notice_src"] = k
            n_acres[m] = pd.to_numeric(snap.Acres.reindex(df.index[m]), errors="coerce").values
            n_legal[m] = snap.LegalDesc.reindex(df.index[m]).fillna("").values
        df["final_value"] = S["PDE"][c["final"]].reindex(df.index).fillna(df.cert_value)
        delta = df.notice_value - df.final_value
        df["reduced"] = delta > 0
        df["reduction"] = delta.where(df.reduced, 0)
        df["reduction_vs_cert"] = (df.notice_value - df.cert_value).clip(lower=0).fillna(0)
        acres = pd.to_numeric(df.Acres, errors="coerce")
        df["geom_change"] = ((acres < n_acres * 0.95) & n_acres.notna()) | (df.final_value == 0)
        df["legal_changed"] = df.LegalDesc.fillna("") != n_legal
        df["flagged"] = df.geom_change | (df.legal_changed & df.reduced)
        df["ptp_client"] = df.index.isin(cl[yr])
        df["tax_year"] = yr
        detail.append(df.drop(columns=["LegalDesc"]).rename_axis("property_id").reset_index())
        for grp, sub in [("PTP clients", df[df.ptp_client]), ("Everyone else", df[~df.ptp_client]), ("All", df)]:
            clean = sub[~sub.flagged]
            rows.append(dict(
                tax_year=str(yr), group=grp,
                commercial_properties=len(sub),
                with_notice_value=int(sub.notice_value.notna().sum()),
                properties_reduced=int(sub.reduced.sum()),
                total_reduction=float(sub.reduction.sum()),
                properties_reduced_excl_flagged=int(clean.reduced.sum()),
                total_reduction_excl_flagged=float(clean.reduction.sum()),
                properties_reduced_vs_certified=int((sub.reduction_vs_cert > 0).sum()),
                total_reduction_vs_certified=float(sub.reduction_vs_cert.sum()),
                ptp_client_accounts_in_county=len(cl[yr]) if grp == "PTP clients" else None,
            ))
    s = pd.DataFrame(rows)
    tot = s.drop(columns="tax_year").groupby("group", as_index=False, sort=False).sum(numeric_only=True)
    tot.insert(0, "tax_year", "2025+2026")
    s = pd.concat([s, tot], ignore_index=True)
    s.to_csv(out / "fortbend_commercial_reductions_summary.csv", index=False)
    pd.concat(detail).to_csv(out / "fortbend_commercial_reductions_detail.csv", index=False)
    pd.set_option("display.width", 250)
    print(s.to_string(index=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
