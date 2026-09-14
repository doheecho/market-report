import os
import re
import csv
import json
import urllib.parse
import pandas as pd

def clean_section(text):
    text = re.sub(r"[^\w\s\(\)&,-]", "", text)
    return text.strip()

def try_read_user_csv(user_csv_path):
    encodings = ["utf-8-sig", "cp949", "utf-16", "utf-8"]
    for enc in encodings:
        try:
            with open(user_csv_path, "r", encoding=enc) as f:
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

def analyze_paragraph(text, vendor_map, keyword_map):
    detected_vendors = set()
    detected_keywords = set()
    
    for pattern, vendor in vendor_map.items():
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
    if re.search(r"samsung|삼성", text, re.IGNORECASE):
        detected_vendors.add("Samsung")
    if re.search(r"sk\s*hynix|sk하이닉스|하이닉스", text, re.IGNORECASE):
        detected_vendors.add("SK하이닉스")

    for pattern, kw in keyword_map.items():
        if re.search(pattern, text, re.IGNORECASE):
            detected_keywords.add(kw)

    return sorted(list(detected_vendors)), sorted(list(detected_keywords))

def calculate_risk_level(keywords):
    high_risk_indicators = {"Shortage", "EOL", "Discommit", "Natural Disaster / Incident"}
    medium_risk_indicators = {"Price Increase", "Lead Time", "Allocation", "Tariff", "Geopolitics / Sanctions"}

    k_set = set(keywords)
    if k_set.intersection(high_risk_indicators):
        return "High"
    elif k_set.intersection(medium_risk_indicators):
        return "Medium"
    else:
        return "Low"

def parse_monthly_file(filepath, year, month, user_cat_map, vendor_map, keyword_map):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split(chr(10))
    records = []
    current_section = "Intro"
    current_subheading = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("# "):
            current_section = line.replace("# ", "").strip()
            current_subheading = ""
            continue

        body_text = None
        has_inline_colon = False
        if (line.startswith("## ") or line.startswith("### ") or line.startswith("#### ")) and ":" in line:
            parts = line.split(":", 1)
            prefix = parts[0].strip()
            suffix = parts[1].strip()
            prefix_clean = re.sub(r'^#+\s*', '', prefix)
            if len(prefix_clean) < 60 and not prefix_clean.endswith(".") and (suffix.endswith(".") or suffix.endswith("]")):
                has_inline_colon = True

        if has_inline_colon:
            parts = line.split(":", 1)
            prefix = parts[0].strip()
            suffix = parts[1].strip()
            prefix_clean = re.sub(r'^#+\s*', '', prefix).strip()
            prefix_clean = re.sub(r'^[-*·•\s]+', '', prefix_clean)
            prefix_clean = re.sub(r'^\d+\.\s+', '', prefix_clean)
            
            if prefix.startswith("## ") or prefix.startswith("##"):
                current_section = prefix_clean
                current_subheading = ""
            elif prefix.startswith("### ") or prefix.startswith("###"):
                current_subheading = prefix_clean
            elif prefix.startswith("#### ") or prefix.startswith("####"):
                current_subheading = prefix_clean
            body_text = suffix
        else:
            if line.startswith("## "):
                cleaned = line.replace("## ", "").strip()
                if cleaned.endswith(".") or cleaned.endswith("]"):
                    body_text = cleaned
                else:
                    current_section = cleaned
                    current_subheading = ""
                    continue
            elif line.startswith("### "):
                cleaned = line.replace("### ", "").strip()
                if cleaned.endswith(".") or cleaned.endswith("]") or "출처" in cleaned:
                    body_text = cleaned
                else:
                    current_subheading = cleaned
                    continue
            elif line.startswith("#### "):
                body_text = line.replace("#### ", "").strip()
            elif line.startswith("---"):
                continue
            else:
                body_text = line

        if "The Greensheet" in body_text or "제공된 정보는" in body_text:
            continue

        combined_context = f"{current_section} | {current_subheading} | {body_text}"
        vendors, keywords = analyze_paragraph(combined_context, vendor_map, keyword_map)
        category_raw = map_category_user(current_section, user_cat_map)
        detected_categories = analyze_categories_for_paragraph(combined_context, category_raw)
        category = detected_categories[0] if detected_categories else "기타"
        risk_level = calculate_risk_level(keywords)

        record = {
            "year": int(year),
            "month": int(month),
            "category": category,
            "detected_categories": detected_categories,
            "section_raw": clean_section(current_section),
            "subheading": current_subheading if current_subheading else clean_section(current_section),
            "text": body_text,
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

def split_raw_full_archive(repo_dir, form_dir):
    archive_path = os.path.join(repo_dir, "data", "raw", "raw_full_archive.md")
    if not os.path.exists(archive_path):
        print(f"- Warning: raw_full_archive.md not found at '{archive_path}'. Skipping split.")
        return
        
    print("- Found raw_full_archive.md. Splitting into monthly source files...")
    with open(archive_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    lines = content.split(chr(10))
    
    current_year = None
    current_month = None
    current_file_lines = []
    
    for line in lines:
        match = re.search(r"^\[The Greensheet\s+(\d{4})년\s+(\d{1,2})월호\]", line)
        if match:
            if current_year and current_month and current_file_lines:
                save_monthly_source(form_dir, current_year, current_month, current_file_lines)
            
            current_year = match.group(1)
            current_month = f"{int(match.group(2)):02d}"
            current_file_lines = [line]
        else:
            if current_year and current_month:
                current_file_lines.append(line)
                
    if current_year and current_month and current_file_lines:
        save_monthly_source(form_dir, current_year, current_month, current_file_lines)

def save_monthly_source(form_dir, year, month, lines):
    filename = f"fusion_greensheet_{year}.{month}.txt"
    dest_path = os.path.join(form_dir, filename)
    
    content = chr(10).join(lines)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

def fetch_public_sheet_csv(spreadsheet_id, sheet_name):
    sheet_name_encoded = urllib.parse.quote(sheet_name)
    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_encoded}"
    try:
        df = pd.read_csv(url)
        df = df.fillna("")
        data_rows = [df.columns.tolist()] + df.values.tolist()
        return data_rows
    except Exception as e:
        print(f"  - Sheet {sheet_name} fetch failed ({e}). Attempting fallback...")
        return None
