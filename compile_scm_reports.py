import os
import re
import csv
import json

# This is the master, self-contained SCM Data Lake Rebuild script!
# Run: "python compile_scm_reports.py" inside your repository to fully rebuild all Master/Gold/History JSONs.

SOURCE_DIR = r"E:\조도희\01.구매기획\01-12.원재료 시황\Fusion Greensheet"
FORM_DIR = SOURCE_DIR
REPO_DIR = os.path.dirname(os.path.abspath(__file__)) # Self-identifying repository directory!
MASTER_OUT_DIR = os.path.join(REPO_DIR, "data", "master")
VIEWS_DIR = os.path.join(REPO_DIR, "data", "views")
CAT_DIR = os.path.join(VIEWS_DIR, "by_category")
VEN_DIR = os.path.join(VIEWS_DIR, "by_vendor")
THEME_DIR = os.path.join(VIEWS_DIR, "by_theme")

# History Output Directories
HISTORY_DIR = os.path.join(VIEWS_DIR, "by_history")
VEND_HIST_DIR = os.path.join(HISTORY_DIR, "vendor")
CAT_HIST_DIR = os.path.join(HISTORY_DIR, "category")

CLI_BACKUP_DIR = r"E:\조도희\11.AI\11-07.CLI"

USER_CSV_PATH = os.path.join(REPO_DIR, "classification_rules.csv")

# 1. Load SCM Master Rules dynamically from JSON Config!
CONFIG_PATH = os.path.join(REPO_DIR, "scm_master_config.json")

VENDOR_MAP = {}
KEYWORD_MAP = {}

if os.path.exists(CONFIG_PATH):
    print(f"- Loading master SCM rules from '{CONFIG_PATH}'...")
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            
        for item in config_data.get("vendor_mappings", []):
            VENDOR_MAP[item["pattern"]] = item["representative"]
            
        for item in config_data.get("theme_mappings", []):
            KEYWORD_MAP[item["pattern"]] = item["representative"]
        print(f"  - Successfully loaded {len(VENDOR_MAP)} vendor rules and {len(KEYWORD_MAP)} theme rules.")
    except Exception as e:
        print(f"  - Error loading json config: {e}. Falling back to default built-ins.")
else:
    print("- Error: scm_master_config.json not found! Falling back to empty defaults.")

from scm_shared import (
    clean_section,
    try_read_user_csv,
    build_user_category_map,
    map_category_user,
    analyze_categories_for_paragraph,
    generate_summary,
    analyze_paragraph,
    calculate_risk_level,
    parse_monthly_file,
    clean_filename,
    split_raw_full_archive,
    save_monthly_source
)


def main():
    print("=========================================================")
    print("🚀 SCM DATA LAKE MASTER COMPILER ACTIVE")
    print("=========================================================")
    # 1. Automatically split single source of truth raw_full_archive.md into monthly txt files!
    split_raw_full_archive(REPO_DIR, FORM_DIR)
    print("=========================================================")
    
    csv_rows = try_read_user_csv(USER_CSV_PATH)
    if not csv_rows:
        print(f"Error: Custom classification CSV not found at '{USER_CSV_PATH}'!")
        return
        
    user_cat_map = build_user_category_map(csv_rows)
    print(f"- Successfully parsed {len(user_cat_map)} custom category mapping rules.")
    
    # 1. Standardize Master JSONs
    files = []
    for filename in sorted(os.listdir(FORM_DIR)):
        match = re.search(r"fusion_greensheet_(\d{4})\.(\d{2})\.txt", filename)
        if match:
            files.append({
                "filename": filename,
                "year": match.group(1),
                "month": match.group(2)
            })

    all_records = []
    by_year_records = {}

    for f_info in files:
        filepath = os.path.join(FORM_DIR, f_info["filename"])
        file_records = parse_monthly_file(filepath, f_info["year"], f_info["month"], user_cat_map, VENDOR_MAP, KEYWORD_MAP)
        
        year = f_info["year"]
        if year not in by_year_records:
            by_year_records[year] = []
            
        by_year_records[year].extend(file_records)
        all_records.extend(file_records)

    # Create master directories if they don't exist
    for d in [MASTER_OUT_DIR, CAT_DIR, VEN_DIR, THEME_DIR, VEND_HIST_DIR, CAT_HIST_DIR]:
        if not os.path.exists(d):
            os.makedirs(d)

    # Overwrite Master Files
    for year, records in sorted(by_year_records.items()):
        dest_path = os.path.join(MASTER_OUT_DIR, f"master_{year}.json")
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    all_dest_path = os.path.join(MASTER_OUT_DIR, "master_all.json")
    with open(all_dest_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"- Compiled {len(all_records)} master records in master_all.json")

    # Clean existing gold view slices
    for d in [CAT_DIR, VEN_DIR, THEME_DIR, VEND_HIST_DIR, CAT_HIST_DIR]:
        for f in os.listdir(d):
            if os.path.isfile(os.path.join(d, f)):
                os.remove(os.path.join(d, f))

    # Category Slices (Cross-sliced!)
    by_category = {}
    for r in all_records:
        cats = r.get("detected_categories", [r["category"]])
        for cat in cats:
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(r)

    for cat_name, cat_records in by_category.items():
        fn = clean_filename(cat_name) + ".json"
        with open(os.path.join(CAT_DIR, fn), "w", encoding="utf-8") as f:
            json.dump(cat_records, f, ensure_ascii=False, indent=2)
    print(f"- Sliced {len(by_category)} categories successfully.")

    # Vendor Slices
    by_vendor = {}
    for r in all_records:
        vendors = r.get("detected_vendors", [])
        for v in vendors:
            if v not in by_vendor:
                by_vendor[v] = []
            by_vendor[v].append(r)

    for ven_name, ven_records in by_vendor.items():
        fn = clean_filename(ven_name) + ".json"
        with open(os.path.join(VEN_DIR, fn), "w", encoding="utf-8") as f:
            json.dump(ven_records, f, ensure_ascii=False, indent=2)
    print(f"- Sliced {len(by_vendor)} vendor views successfully.")

    # Theme Slices
    themes = {
        "leadtime_risk.json": lambda r: any(kw in r["detected_keywords"] for kw in ["Lead Time", "Allocation", "Discommit"]),
        "eol_tracker.json": lambda r: "EOL" in r["detected_keywords"],
        "price_alerts.json": lambda r: any(kw in r["detected_keywords"] for kw in ["Price Increase", "Price Decrease"]),
        "disaster_and_accidents.json": lambda r: any(kw in r["detected_keywords"] for kw in ["Natural Disaster / Incident", "Quality / Defect"]),
        "geopolitics_and_tariffs.json": lambda r: any(kw in r["detected_keywords"] for kw in ["Tariff", "Geopolitics / Sanctions"]),
        "corporate_actions.json": lambda r: any(kw in r["detected_keywords"] for kw in ["M&A", "Production Cut", "Capacity Expansion"]),
        "high_risk_dashboard.json": lambda r: r.get("risk_level") == "High"
    }

    for filename, filter_func in themes.items():
        theme_records = [r for r in all_records if filter_func(r)]
        with open(os.path.join(THEME_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(theme_records, f, ensure_ascii=False, indent=2)
    print("- Sliced 7 risk themes successfully.")

    # 3. Compile SCM Chronological Timelines
    sorted_records = sorted(all_records, key=lambda x: (x["year"], x["month"]))
    
    # Vendor Timelines
    by_vendor_timeline = {}
    for r in sorted_records:
        vendors = r.get("detected_vendors", [])
        for v in vendors:
            if v not in by_vendor_timeline:
                by_vendor_timeline[v] = []
            event = {
                "date": f"{r['year']}.{r['month']:02d}",
                "category": r["category"],
                "detected_categories": r.get("detected_categories", [r["category"]]),
                "risk_level": r["risk_level"],
                "summary": generate_summary(r),
                "text": r["text"]
            }
            by_vendor_timeline[v].append(event)
            
    for ven_name, events in by_vendor_timeline.items():
        fn = clean_filename(ven_name) + "_history.json"
        with open(os.path.join(VEND_HIST_DIR, fn), "w", encoding="utf-8") as f:
            json.dump({"vendor": ven_name, "total_milestones": len(events), "history": events}, f, ensure_ascii=False, indent=2)
            
    # Category Timelines
    by_category_timeline = {}
    for r in sorted_records:
        cats = r.get("detected_categories", [r["category"]])
        for cat in cats:
            if cat not in by_category_timeline:
                by_category_timeline[cat] = []
            event = {
                "date": f"{r['year']}.{r['month']:02d}",
                "detected_vendors": r.get("detected_vendors", []),
                "risk_level": r["risk_level"],
                "summary": generate_summary(r),
                "text": r["text"]
            }
            by_category_timeline[cat].append(event)
            
    for cat_name, events in by_category_timeline.items():
        fn = clean_filename(cat_name) + "_history.json"
        with open(os.path.join(CAT_HIST_DIR, fn), "w", encoding="utf-8") as f:
            json.dump({"category": cat_name, "total_milestones": len(events), "history": events}, f, ensure_ascii=False, indent=2)
    print(f"- Compiled {len(by_vendor_timeline)} vendor histories & {len(by_category_timeline)} category histories.")

    # Dual-saving consistency
    backup_path = os.path.join(CLI_BACKUP_DIR, "master_all.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    cli_theme_backup = os.path.join(CLI_BACKUP_DIR, "views", "by_theme")
    if not os.path.exists(cli_theme_backup):
        os.makedirs(cli_theme_backup)
        
    for filename, filter_func in themes.items():
        theme_records = [r for r in all_records if filter_func(r)]
        with open(os.path.join(cli_theme_backup, filename), "w", encoding="utf-8") as f:
            json.dump(theme_records, f, ensure_ascii=False, indent=2)

    cli_history_backup = os.path.join(CLI_BACKUP_DIR, "views", "by_history")
    if not os.path.exists(cli_history_backup):
        os.makedirs(cli_history_backup)
    with open(os.path.join(cli_history_backup, "timeline_stats.json"), "w", encoding="utf-8") as f:
        json.dump({
            "total_records": len(sorted_records),
            "vendors": {v: len(evs) for v, evs in by_vendor_timeline.items()},
            "categories": {c: len(evs) for c, evs in by_category_timeline.items()}
        }, f, ensure_ascii=False, indent=2)

    print("\n=========================================================")
    print("✨ SUCCESS: REBUILD COMPLETE & DUAL-SAVED SUCCESSFULLY!")
    print("=========================================================")

if __name__ == "__main__":
    main()
