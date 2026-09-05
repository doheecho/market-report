# My Market Intelligence (Fusion Worldwide Greensheet Data Lake) 🚀

이 저장소는 **Fusion Worldwide Greensheet** 월간 시장 시황 보고서 데이터를 체계적으로 관리하고, AI 파이프라인을 통해 정규화 및 분석하기 위한 **Medallion Architecture (Data Lake) 표준 저장소**입니다.

## 🗂️ 저장소 아키텍처 및 디렉토리 구조

```text
my-market-intelligence/
├── data/
│   ├── raw/                      # [Level 1: Bronze] 원본 텍스트 보관소
│   │   ├── raw_full_archive.md   # 전체 통합 백업본
│   │   ├── raw_2020.md           # 2020년 연간 시황 (4~12월)
│   │   ├── raw_2021.md           # 2021년 연간 시황
│   │   ├── raw_2022.md           # 2022년 연간 시황
│   │   ├── raw_2023.md           # 2023년 연간 시황
│   │   ├── raw_2024.md           # 2024년 연간 시황
│   │   ├── raw_2025.md           # 2025년 연간 시황
│   │   ├── raw_2026.md           # 2026년 연간 시황 (1~8월)
│   │   └── monthly/              # 월별 정돈된 고품격 마크다운 개별 파일 (.md)
│   │
│   ├── master/                   # [Level 2: Silver] AI 파싱 표준 마스터 레코드 (JSON)
│   │   ├── master_2020.json
│   │   ├── master_2021.json
│   │   └── master_all.json       # 전체 마스터 병합 JSON
│   │
│   └── views/                    # [Level 3: Gold] 대시보드 및 리포트 연동 전용 슬라이스 JSON
│       ├── by_category/          # 품목군별 (storage.json, memory.json, cpu.json, ic.json)
│       ├── by_vendor/            # 제조사별 (samsung.json, intel.json, avx.json, tsmc.json)
│       └── by_theme/             # 트랙킹 테마별 (leadtime_risk.json, eol_tracker.json, logistics.json)
```

---

## 💡 Medallion Architecture 가치

1. **Bronze (Raw Data):**
   - 수집된 원천 데이터를 가감 없이 표준 마크다운 파일로 정렬 보관합니다.
   - 향후 AI 모델 고도화나 스키마 변경 시, 언제든지 원천 데이터를 다시 인덱싱(Re-indexing)할 수 있어 데이터 소실이 전혀 발생하지 않는 안전한 영구 소스 역할을 합니다.

2. **Silver (Master Records):**
   - LLM 파이프라인(JSON Schema, Enum validation 등)을 통해 이종 동의어(e.g., `SAMSUNG`, `삼성`, `Samsung Electronics` -> `Samsung`)를 표준 명칭으로 통합하여 정규화된 일관된 원장의 JSON을 구축합니다.

3. **Gold (Analytical Views):**
   - 최종 마케팅 분석 모델, 공급망 리스크 점검 모듈 및 시황 대시보드 화면으로 초고속(0ms) 수준 연계를 제공하는 슬라이스 뷰 데이터입니다.

---

## 🛠️ 향후 실행 가이드라인

1. **AI Parsing 파이프라인 가동:**
   - `data/raw/` 하위의 연도별 마크다운 파일을 순차적으로 LLM 프롬프트에 제공해 지정된 스키마 JSON 형태로 가공하여 `data/master/` 폴더에 안착시킵니다.
2. **Standardization & Python Validation:**
   - 변환된 JSON들을 파이썬 후처리 매퍼(`standard_mapper.py`)를 통해 대소문자 및 예외 문자열 정합성을 100% 무결하게 보정합니다.
3. **Slicing & Dashboard Bind:**
   - 최종 슬라이싱된 `views/` 데이터를 깃허브 Pages나 정적 API 형태로 대시보드 웹앱에 직접 비동기 페칭하여 시인성 높은 시황 맵과 추이 대시보드를 구동합니다.
