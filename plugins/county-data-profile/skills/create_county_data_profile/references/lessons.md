# What came up profiling CAD files, and what to look for in the next county

Every point below was found in a real county's files. None of it is a rule about a county: check each one
against the files in front of you.

## Reading the files
- **Check encoding and delimiter before profiling**: `file <path>` and `head -c 300 <path> | xxd`.
  - Agent Summary `.txt` files were **UTF-16LE, pipe-delimited** → `"read": "pipe_utf16"`.
  - The exemptions `.txt` was **Latin-1, pipe-delimited** → `"pipe_latin1"`.
  - CSV exports made from `.xlsx` (pandas `to_csv`) are UTF-8 with no BOM → `"csv"`.
- **`strict_mode=false` can silently drop rows.** In one county's quoted, comma-delimited Latin-1 CSVs it lost
  38,073 of 806,563 `ACCOUNT_INFO` rows and logged no rejects. Always compare `rows` with `wc -l` minus the
  header. When they differ, use strict mode (`{"opts": "encoding='latin-1'"}`), which read every row there.
  Dates there were `MM/DD/YYYY`, which the profiler also reads.
- **Excel sources**: profile the CSV export, not the `.xlsx`. Still open the workbook
  (`openpyxl.load_workbook(path, read_only=True).sheetnames`), because some years ship a
  **Data Dictionary** sheet. Use its text, word for word, as the column tooltips, and reuse it for the
  matching columns of earlier years.
- **Fixed-width values** are padded with spaces. The profiler keeps the padding, so those values count as
  filled and may type as Text rather than Integer. Say so in a note rather than trimming.
- **Broken lines**: a line break inside a text field (`Notes`, listing descriptions) splits a record.
  The profiler keeps going, and `rejected` / `rej_sample` in profile.json show it. Say so in a note
  ("N lines could not be read ...").
- **Shifted rows**: a stray `|` in a text field moves the rest of that row one column right. A numeric
  column then shows a few text values (`ASN` holding `F1`). Pin the real type with `force` and write a note.

## Values that need a note
- Placeholders:
  - dates `1900-01-01` and `12-31-1900`
  - years `9999`, `0`
  - coordinates written as a **run of 32 zeros** instead of blank
  - `N/A` in date and deed fields
- Typos: years like 2203, 20224 or 9223, and dates from 1776.
- Columns that are filled but always zero (ceiling amounts). Columns blank in every row (the page lists
  these automatically).
- **Folder year ≠ data year.** The "2025" Agent Summary folder had `TaxYear` 2026 in every row. Always
  check the year column against the folder name.
- **Suspiciously small files.** Review Board 2025 had 58 cases against 340,602 the year before. Compare
  each year's row count with the year before.
- Big shifts between years:
  - fill rate (Exemptions blank names went from 22% to 42%)
  - a column filled one year and empty the next
  - number formats (4 decimals → whole numbers)
  - renamed headers, and renamed files (Residential Features Value → Residential Improvement Details)
- Charts include zeros and every year, so a placeholder like `9999` shows as its own bar.
- `find_anomalies.py` prints most of these. Before quoting a number in a note, confirm it with a DuckDB
  query, for example:
  ```python
  duckdb.sql("select count(*), count(distinct Account_Num), count(*) filter (where Exemption is null) "
             "from read_csv('...', all_varchar=true, ...)").fetchall()
  ```

## Joins worth checking and stating
- Account number name and format in each file: `Account_Num`, `AccountNumber`, `PIN`. Look for leading
  zeros, and for 8-digit numbers that load as integers. Test the join between files (for example, how many
  comp-attribute PINs are in Property Data).
- **Portal API ids**: in one portal, `pID` was the CAD account number. Of 100 sample properties, 98 matched the
  2026 roll and 100 matched the 2025 roll once padded to 8 digits. `pAccountID` is internal and matches
  nothing. Check this the same way for every new portal (pad, then join to the latest roll), and put the
  result in the API notes.

## No transformation
- The page documents the data as published. Nothing is cleaned, trimmed, masked, redacted, shortened or
  dropped from a chart: owner names, addresses, zeros, `1900-01-01`, year `9999` and padded values all
  show as they are. Don't add a county script that edits profile.json values.
- Quirks go in notes, never in the values.
- API examples can hold real-looking tokens or pre-signed links. After building, grep the HTML for `eyJ`,
  `X-Amz-` and `password`, and tell the user what you found before publishing. Don't remove it yourself.

## Descriptions (tooltips)
- Every column needs one; `build_page.py` fails until it has them. Write short, plain-language meanings
  from the column name, sample values and Texas property-tax context. Prefer the CAD's own data
  dictionary when there is one.
- Tell the user which descriptions are best guesses: internal codes like `AIN`, `ASN`, `PIDN` and
  `SiteRating`.
- `examples/` already has about 480 descriptions for common Texas CAD and
  TrueProdigy portal fields. Copy the ones that apply.

## Conversions
- **Detect encoding from the whole file, not an assumption.** A submission file assumed to be Latin-1 was really
  UTF-8: `½` came out as `Â½` in a handful of rows. `split_record_types.py` and `to_csv_gz.py` read UTF-8 when
  the whole file decodes, else Latin-1. When a profile shows `Ã`, `Â` or `â€` sequences, re-read with the right encoding.
- **Pin the quote character.** With auto-detection DuckDB once took `'` as the quote in a names file and mangled
  values like `AUSTIN'S COLONY`. Converted `.csv.gz` files use the `{"opts": "delim=',', quote='\"', escape='\"', ..."}`
  preset `add_tables.py` writes.
- **JSON exports**: one object per property, with nested lists (owners, taxing units, valuations, deeds, appeals
  ...). Each list becomes a table that joins back on the record key plus `<list>_i` positions. Lists of plain values
  stay JSON text in one column. A multi-GB export takes minutes with all cores; run two exports at once if disk
  allows (the parts need about the size of the output again).
- **Mixed record types** (state submissions): the first field names the record type; each type's layout comes from
  the manual's appendix tables, and the field count grows across manual releases, so older years use the first N
  fields. Check one account across years to confirm the fields line up before trusting the names.
- **Reports split into parts** with one header (`name_1.csv` ... `name_4.csv`) profile as one table: join them
  with `to_csv_gz.py`, which checks the headers match.
- **Keep the original download.** Converted tables go to their own folder; the page names the original file
  (`raw`) and never our converted path.

## Website and Drive
- Websites rename re-uploads (`file-1.pdf`) and sometimes point a link at a newer upload than the one we profiled.
  Keep the website link, say which snapshot we profiled in the catalog `note`, and tell the user.
- A website file we don't have locally is still listed in the catalog (role doc or data without `tables`), so the
  team sees the whole page; say which ones are missing.
