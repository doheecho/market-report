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

VENDOR_MAP = {
    r"samsung|삼성": "삼성",
    r"micron|마이크론": "Micron",
    r"hynix|하이닉스": "SK하이닉스",
    r"intel|인텔|altera|알테라": "Intel",
    r"nvidia|엔비디아": "Nvidia",
    r"amd|advanced micro devices|xilinx|자일링스|xlinx": "Amd",
    r"broadcom|브로드컴": "Broadcom",
    r"infineon|인피니언": "Infineon",
    r"nexperia|넥스페리아|\bnxp\b|에스엔피": "Nexperia",
    r"lattice|래티스|lattice\s*semiconductor": "Lattice",
    r"toshiba|도시바": "Toshiba",
    r"seagate|씨게이트": "Seagate",
    r"solidigm|솔일다임": "Solidigm",
    r"kioxia|키옥시아": "Kioxia",
    r"murata|무라타": "Murata",
    r"taiyo yuden|taiyo|타이요\s*유덴": "Taiyo Yuden",
    r"yageo|야게오": "Yageo",
    r"panasonic|파나소닉": "Panasonic",
    r"kemet|케멧": "Kemet",
    r"qorvo|코보": "Qorvo",
    r"realtek|리얼텍": "Realtek",
    r"sony|소니": "Sony",
    r"winbond|윈본드": "Winbond",
    r"nanya|남야": "Nanya",
    r"coherent|finisar|코히런트|피니사": "Coherent",
    r"macnica|맥니카": "Macnica",
    r"arrow|애로": "Arrow",
    r"microchip|마이크로칩": "Microchip",
    r"on[-_\s]*semi|onsemi|온세미": "Onsemi",
    r"supermicro|슈퍼마이크로": "Supermicro",
    r"huawei|화웨이": "Huawei",
    r"mellanox|멜라녹스": "Mellanox",
    r"inspur|인스퍼": "Inspur",
    r"qlogic|큐로직": "QLogic",
    r"renesas|르네사스": "Renesas",
    r"mediatek|mi디어텍": "Mediatek"
}

KEYWORD_MAP = {
    r"가격\s*인상|비용\s*인상|단가\s*인상|가격\s*상승|인상률|가격\s*조정|오름세": "Price Increase",
    r"가격\s*인하|비용\s*인하|가격\s*하락|비용\s*하락|내림세|디플레이션": "Price Decrease",
    r"리드\s*타임|리드타임|배송\s*기간|납기|배송\s*지연|납품\s*일정": "Lead Time",
    r"단종|eol|지원\s*종료|수명\s*종료|생산\s*종료": "EOL",
    r"부족|공급\s*부족|품귀|제약|수급\s*문제|공백": "Shortage",
    r"할당|배정": "Allocation",
    r"디커밋|공급\s*확약\s*철회|납품\s*취소": "Discommit",
    r"지진|화재|태풍": "Natural Disaster / Incident",
    r"관세": "Tariff",
    r"인수|합병|m&a|인수\s*제안|합병\s*추진": "M&A",
    r"감산|생산\s*감축|생산량을\s*줄이|생산\s*축소": "Production Cut",
    r"생산\s*라인\s*확장|증산|투자\s*계획|생산량\s*확대|생산\s*능력\s*확대": "Capacity Expansion",
    r"수출\s*규제|제재|미중\s*기술|수출\s*제한": "Geopolitics / Sanctions",
    r"결함|품질\s*문제|품질\s*우려|진품성\s*우려": "Quality / Defect"
}

def clean_section(text):
    text = re.sub(r"[^\w\s\(\)&,-]", "", text)
    return text.strip()

def try_read_user_csv():
    encodings = ["utf-8-sig", "cp949", "utf-16", "utf-8"]
    for enc in encodings:
        try:
            with open(USER_CSV_PATH, "r", encoding=enc) as f:
                reader = csv.reader(f)
                rows = list(reader)
                return rows
        except Exception:
            continue
    return None

def build_user_category_map(csv_rows):
    cat_map = {}
    for r in csv_rows[1:]:
        if len(r) > 3 and r[0] == "대분류(Section)":
            raw_sec = r[1].strip()
            new_cat = r[3].strip()
            if raw_sec and new_cat:
                cat_map[clean_section(raw_sec)] = new_cat
    return cat_map

def map_category_user(section_raw, user_cat_map):
    cleaned = clean_section(section_raw)
    if cleaned in user_cat_map:
        return user_cat_map[cleaned]
    for raw_name, new_cat in user_cat_map.items():
        if raw_name.lower() in cleaned.lower() or cleaned.lower() in raw_name.lower():
            return new_cat
    return "Other"

def analyze_categories_for_paragraph(text, original_category):
    detected = set()
    if original_category and original_category != "기타":
        detected.add(original_category)
        
    lower_text = text.lower()
    
    if re.search(r"회로\s*기판|pcb", lower_text):
        detected.add("PCB")
        
    if (any(w in lower_text for w in ["ic", "집적회로", "집적 회로", "pmic", "mcu", "포토커플러", "센서", "sensor", "아날로그", "반도체", "칩셋", "트랜시버", "transceiver"]) or 
        re.search(r"vertex|kintex|spartan|ultra\s+scale|fpga", lower_text)):
        detected.add("IC")
        
    if any(w in lower_text for w in ["ssd", "hdd", "스토리지", "저장 장치", "저장장치", "디스크", "하드디스크", "nvme"]) or re.search(r"하드\s+드라이브", lower_text):
        detected.add("Storage")
        
    if any(w in lower_text for w in ["gpu", "그래픽", "가속기", "blackwell", "h200", "h100", "a100", "rtx", "블랙웰", "jetson"]):
        detected.add("GPU")
        
    if any(w in lower_text for w in ["dram", "hbm", "ddr", "rdimm", "메모리", "플래시", "flash", "nand", "emmc", "nor"]):
        detected.add("Memory")
        
    if any(w in lower_text for w in ["mlcc", "수동소자", "수동 소자", "커패시터", "capacitor", "탄탈", "콘덴서"]):
        detected.add("Passive")
        
    if any(w in lower_text for w in ["cpu", "중앙처리장치", "epyc", "xeon", "turin", "genoa", "프로세서", "스레드리퍼"]):
        detected.add("CPU")
        
    if not detected:
        detected.add("기타")
        
    return sorted(list(detected))

def generate_summary(r):
    sub = r.get("subheading", "").strip()
    if sub:
        cleaned_sub = re.sub(r"^\d+[\s\.\,\-\_]*", "", sub)
        return cleaned_sub
    text = r.get("text", "").strip()
    first_sentence = text.split(".")[0].strip()
    if first_sentence:
        cleaned_sent = re.sub(r"^\d+[\s\.\,\-\_]*", "", first_sentence)
        if not cleaned_sent.endswith("."):
            cleaned_sent += "."
        return cleaned_sent
    return text[:80] + "..."

def analyze_paragraph(text):
    detected_vendors = set()
    detected_keywords = set()
    
    for pattern, vendor in VENDOR_MAP.items():
        if re.search(pattern, text, re.IGNORECASE):
            detected_vendors.add(vendor)
            
    if re.search(r"texas\s*instruments", text, re.IGNORECASE) or re.search(r"텍사스\s*인스트루먼트", text, re.IGNORECASE) or re.search(r"\bTI\b", text):
        detected_vendors.add("Texas Instruments")
    if re.search(r"analog\s*devices", text, re.IGNORECASE) or re.search(r"아날로그\s*디바이스", text, re.IGNORECASE) or re.search(r"\bADI\b", text) or re.search(r"maxim|맥심", text, re.IGNORECASE):
        detected_vendors.add("Analog Devices")
    if re.search(r"western\s*digital", text, re.IGNORECASE) or re.search(r"웨스턴\s*디지털", text, re.IGNORECASE) or re.search(r"\bWD\b", text):
        detected_vendors.add("Western Digital")
    if re.search(r"stmicroelectronics", text, re.IGNORECASE) or re.search(r"\bSTM\b", text):
        detected_vendors.add("STMicroelectronics")
    if re.search(r"tsmc|티에스엠씨", text, re.IGNORECASE) or re.search(r"\bTSMC\b", text):
        detected_vendors.add("TSMC")
    if re.search(r"avx", text, re.IGNORECASE) or re.search(r"\bAVX\b", text):
        detected_vendors.add("AVX")
    if re.search(r"byd|비야디", text, re.IGNORECASE) or re.search(r"\bBYD\b", text):
        detected_vendors.add("BYD")
        
    for pattern, kw in KEYWORD_MAP.items():
        if re.search(pattern, text, re.IGNORECASE):
            detected_keywords.add(kw)
            
    return sorted(list(detected_vendors)), sorted(list(detected_keywords))

def calculate_risk_level(keywords):
    high_risk_indicators = {"Shortage", "EOL", "Discommit", "Natural Disaster / Incident", "Quality / Defect"}
    medium_risk_indicators = {"Price Increase", "Lead Time", "Allocation", "Tariff", "Geopolitics / Sanctions"}
    
    k_set = set(keywords)
    if k_set.intersection(high_risk_indicators):
        return "High"
    elif k_set.intersection(medium_risk_indicators):
        return "Medium"
    else:
        return "Low"

def parse_monthly_file(filepath, year, month, user_cat_map):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split("\n")
    records = []
    
    current_section = "Intro"
    current_subheading = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("### "):
            current_section = line.replace("### ", "").strip()
            current_subheading = ""
            continue
        elif line.startswith("---"):
            continue
        elif line.startswith("##"):
            continue
            
        if line.startswith("#### "):
            current_subheading = line.replace("#### ", "").strip()
            continue
            
        if "The Greensheet는" in line or "제공된 정보는" in line:
            continue
            
        vendors, keywords = analyze_paragraph(line)
        category_raw = map_category_user(current_section, user_cat_map)
        
        detected_categories = analyze_categories_for_paragraph(line, category_raw)
        category = detected_categories[0] if detected_categories else "기타"
        
        risk_level = calculate_risk_level(keywords)
        
        record = {
            "year": int(year),
            "month": int(month),
            "category": category, 
            "detected_categories": detected_categories, 
            "section_raw": clean_section(current_section),
            "subheading": current_subheading,
            "text": line,
            "detected_vendors": vendors,
            "detected_keywords": keywords,
            "risk_level": risk_level
        }
        records.append(record)
        
    return records

def clean_filename(name):
    if name == "삼성":
        return "samsung"
    if name == "SK하이닉스":
        return "sk_hynix"
    if name == "기타":
        return "other"
    name = name.lower()
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name)
    name = re.sub(r"[^a-z0-9]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def main():
    print("=========================================================")
    print("🚀 SCM DATA LAKE MASTER COMPILER ACTIVE")
    print("=========================================================")
    
    csv_rows = try_read_user_csv()
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
        file_records = parse_monthly_file(filepath, f_info["year"], f_info["month"], user_cat_map)
        
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
