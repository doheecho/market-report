# 🏗️ SCM 시황 데이터 레이크 & Risk 대시보드 아키텍처 분석 가이드

본 문서는 `my-market-intelligence` 프로젝트의 전체 디렉토리/파일 구조와 특히 **핵심 파이썬(Python) 파이프라인 스크립트 4종의 역할, 내부 로직 및 상호작용**을 상세하게 분석한 통합 가이드입니다.

---

## 📌 목차
1. [프로젝트 개요 및 데이터 아키텍처](#1-프로젝트-개요-및-데이터-아키텍처)
2. [전체 파일 및 폴더 구조 상세](#2-전체-파일-및-폴더-구조-상세)
3. [Python 파이프라인 스크립트 심층 분석](#3-python-파이프라인-스크립트-심층-분석)
   - [3.1 `run_pipeline.py` (통합 실행 오케스트레이터)](#31-run_pipelinepy-통합-실행-오케스트레이터)
   - [3.2 `scm_shared.py` (공통 유틸리티 및 전처리 모듈)](#32-scm_sharedpy-공통-유틸리티-및-전처리-모듈)
   - [3.3 `compile_scm_reports.py` (시황 보고서 코어 컴파일러)](#33-compile_scm_reportspy-시황-보고서-코어-컴파일러)
   - [3.4 `compile_scm_risk_data.py` (4대 Risk 도메인 프리컴파일러)](#34-compile_scm_risk_datapy-4대-risk-도메인-프리컴파일러)
4. [스크립트 간 호출 관계 및 실행 흐름도](#4-스크립트-간-호출-관계-및-실행-흐름도)
5. [설정 파일 및 규칙 매핑 매커니즘](#5-설정-파일-및-규칙-매핑-매커니즘)
6. [배포 및 운영 워크플로우](#6-배포-및-운영-워크플로우)

---

## 1. 프로젝트 개요 및 데이터 아키텍처

본 시스템은 반도체 및 전자부품 원재료 시황 보고서(The Greensheet) 원문을 수집·분석하여, SCM 담당자가 신속하게 의사결정을 내릴 수 있도록 돕는 **SCM Risk 대시보드 SPA(Single Page Application) 및 데이터 레이크**입니다.

### Medallion 데이터 아키텍처 (Bronze → Silver → Gold)

```
[Raw Sources] ────────────────────────────────────────────────────────┐
 │ - data/raw/monthly/*.md, *.txt (월별 원고)                          │
 │ - data/raw/raw_full_archive.md (단일 진실 원천 통합 마크다운)         │
 └────────────────────────────────────────────────────────────────────┘
                                   │
                           [Bronze Layer: 정제]
                                   ▼
 [Silver Layer: 통합 마스터] ──────────────────────────────────────────┐
 │ - data/master/master_YYYY.json (연도별 정형 JSON)                   │
 │ - data/master/master_all.json (7개년 전수 통합 원장)                 │
 └────────────────────────────────────────────────────────────────────┘
                                   │
              [Gold Layer: 프론트엔드 서빙용 슬라이스 API]
                                   ▼
 ┌───────────────────────┬────────────────────────┬──────────────────┐
 │ by_category/*.json    │ by_vendor/*.json       │ by_theme/*.json  │
 │ (8대 품목군별 뷰)      │ (40+ 제조사별 뷰)      │ (7대 테마별 뷰)   │
 ├───────────────────────┼────────────────────────┴──────────────────┤
 │ by_history/           │ Risk 도메인 JSONs                         │
 │ ├─ vendor/*_history   │ ├─ geopolitics_risk.json, partners.json   │
 │ └─ category/*_history │ ├─ stability_risk.json, cost_market.json  │
 │ (연대기 역사 타임라인)  │ └─ procurement_risk.json, ai_advisor.json │
 └───────────────────────┴───────────────────────────────────────────┘
```

---

## 2. 전체 파일 및 폴더 구조 상세

```text
my-market-intelligence/
│
├── 📜 실행 및 빌드 스크립트
│   ├── run_pipeline.py          # [파이프라인] 전체 데이터 빌드 총괄 마스터 러너
│   ├── compile_scm_reports.py   # [파이썬 엔진] Greensheet 시황 보고서 컴파일러
│   ├── compile_scm_risk_data.py # [파이썬 엔진] 4대 Risk 뷰 및 AI 어드바이저 프리컴파일러
│   ├── scm_shared.py            # [공통 라이브러리] 텍스트 정제/정규식/파서 유틸리티
│   └── git_push.bat             # [배치 파일] Git 커밋 및 GitHub 자동 푸시 스크립트
│
├── ⚙️ 규칙 및 설정 파일
│   ├── classification_rules.csv # 원문 섹션 대분류 -> 8대 정규 품목군 매핑 테이블
│   ├── scm_master_config.json   # 벤더/키워드 정규식 규칙 및 외부 시트 연동 설정
│   └── GEMINI.md                # AI 어시스턴트 및 개발자 작업 지침서
│
├── 🌐 웹 프론트엔드 (GitHub Pages 배포)
│   ├── index.html               # 대시보드 단일 페이지 웹 애플리케이션 (SPA)
│   ├── manifest.webmanifest     # PWA 웹 앱 매니페스트
│   ├── favicon.svg              # 파비콘 벡터 아이콘
│   └── icon-*.png               # PWA/모바일용 해상도별 앱 아이콘
│
├── 🤖 CI/CD 배포 자동화
│   └── .github/workflows/
│       └── pages.yml            # GitHub Pages 자동 배포 액션 워크플로우
│
└── 📁 data/ (데이터 레이크)
    ├── raw/                     # [Bronze] 정제 전/후 텍스트 및 마크다운 원고
    │   ├── raw_full_archive.md  # 7개년 전체 Greensheet 통합 마크다운 아카이브
    │   ├── raw_YYYY.md          # 연도별 아카이브
    │   └── monthly/             # 70개 월별 개별 파일 (fusion_greensheet_YYYY.MM.txt/.md)
    │
    ├── master/                  # [Silver] 정형화된 통합 마스터 JSON 원장
    │   ├── master_all.json      # 전체 기간 전수 레코드 통합 원장
    │   └── master_YYYY.json     # 2020~2026 연도별 마스터 파일
    │
    └── views/                   # [Gold] index.html이 비동기 fetch하는 슬라이스 API
        ├── ai_advisor.json      # 상단 실시간 SCM AI 조언 및 핵심 뉴스 피드
        ├── geopolitics_risk.json        # 지정학적 위험 지도 좌표 및 데이터
        ├── geopolitics_partners.json    # 지정학적 위험 협력사 10열 분석 테이블
        ├── management_stability.json    # 경영안정 조기경보 및 협력사 테이블
        ├── stability_risk.json          # 경영안정성 종합 JSON
        ├── cost_market_risk.json        # 환율 및 원가인상 요청/협력사 분석
        ├── currency_data.json           # 환율(USD, EUR, JPY) 시계열 데이터
        ├── procurement_risk.json        # 납기/리드타임 변동 및 공급망 병목 분석
        │
        ├── by_category/         # 8대 품목군 슬라이스 (cpu, gpu, ic, memory, passive, pcb, storage, other)
        ├── by_vendor/           # 43개 제조사별 슬라이스 (samsung, sk_hynix, tsmc, intel, ti, ...)
        ├── by_theme/            # 7대 리스크 테마 (leadtime, eol, price, disaster, geopolitics, corporate, high_risk)
        └── by_history/          # 연대기적 역사 타임라인 JSON
            ├── category/        # 품목군별 7개년 연대기 타임라인
            └── vendor/          # 제조사별 7개년 연대기 타임라인
```

---

## 3. Python 파이프라인 스크립트 심층 분석

### 3.1 `run_pipeline.py` (통합 실행 오케스트레이터)
* **목적:** 데이터 갱신 시 여러 개로 분리된 파이썬 컴파일러를 한 번의 명령어로 안전하게 순차 실행하는 **마스터 엔트리포인트**.
* **주요 동작 원리:**
  1. 현재 스크립트가 위치한 디렉토리로 작업 경로(`os.chdir`)를 자동 전환합니다.
  2. 현재 환경의 파이썬 인터프리터(`sys.executable`)를 사용하여 다음 두 스크립트를 순서대로 실행합니다:
     - **1단계:** `compile_scm_reports.py` (시황 보고서 코어 및 히스토리 빌드)
     - **2단계:** `compile_scm_risk_data.py` (4대 Risk 뷰 및 AI 어드바이저 프리컴파일)
  3. 만약 1단계에서 에러가 발생하면 2단계를 진행하지 않고 즉시 종료(`sys.exit(1)`)하여 데이터 불일치를 방지합니다.

---

### 3.2 `scm_shared.py` (공통 유틸리티 및 전처리 모듈)
* **목적:** 모든 컴파일러 스크립트에서 공유하는 **핵심 파싱, 정규식 판정, 텍스트 정제 엔진**.
* **핵심 함수별 역할:**

| 함수명 | 역할 및 주요 로직 |
| :--- | :--- |
| `try_read_user_csv(path)` | 인코딩 충돌 방지를 위해 `utf-8-sig`, `cp949`, `utf-16`, `utf-8` 순으로 시도하여 `classification_rules.csv`를 안전하게 로드합니다. |
| `build_user_category_map(rows)` | CSV에서 "대분류(Section)" 행들을 파싱하여 `{원문 섹션명: 표준 8대 품목명}` 딕셔너리를 빌드합니다. |
| `map_category_user(section, map)` | 텍스트 정제 후 매핑 테이블과 대조하여 표준 품목명을 반환하며, 일치하지 않으면 부분 일치를 탐색하고 없으면 "Other"를 반환합니다. |
| `analyze_categories_for_paragraph(text, orig_cat)` | 한 단락 내에 언급된 키워드(MLCC, DRAM, HBM, GPU, PCB, MCU 등)를 기반으로 **복합 품목(Cross-category)**을 다중 감지하여 리스트로 반환합니다. |
| `analyze_paragraph(text, vendor_map, keyword_map)` | **정규식 기반 벤더 및 키워드 감지 엔진**입니다.<br>• 단형 벤더명(TI, ADI, WD, ST, TSMC, TDK 등)의 오탐지를 막기 위해 `(?<![a-zA-Z])TI(?![a-zA-Z])`와 같이 전후방 탐색 정규식을 적용합니다.<br>• 한국어 조사(의, 는, 가, 에 등)와 붙어 있어도 완벽히 감지하도록 처리되어 있습니다. |
| `calculate_risk_level(keywords)` | 검출된 키워드를 기반으로 위험도를 3단계로 판정합니다:<br>• **High:** Shortage, EOL, Discommit, Natural Disaster<br>• **Medium:** Price Increase, Lead Time, Allocation, Tariff, Geopolitics<br>• **Low:** 기타 |
| `generate_summary(record)` | 타임라인 렌더링용으로 소제목 또는 첫 문장을 추출하여 **80자 내외의 정제된 요약문**을 생성합니다. |
| `parse_monthly_file(path, year, month, ...)` | `#`, `##`, `###` 마크다운 및 텍스트 문단을 읽어와 섹션, 소제목, 본문 텍스트를 분리하고, 키워드/벤더/리스크 레벨을 태깅한 정형 레코드 딕셔너리 리스트로 변환합니다. |
| `split_raw_full_archive(repo_dir, form_dir)` | 단일 통합 아카이브 파일인 `raw_full_archive.md`를 정규식(`[The Greensheet YYYY년 MM월호]`)으로 감지하여 월별 파일(`fusion_greensheet_YYYY.MM.txt`)로 자동 분할 저장합니다. |

---

### 3.3 `compile_scm_reports.py` (시황 보고서 코어 컴파일러)
* **목적:** Greensheet 월별 원고를 읽어 Medallion 아키텍처의 **Silver 마스터 원장과 Gold 시황 뷰팩/히스토리**를 생성합니다.
* **주요 5단계 빌드 공정:**
  1. **설정 로딩:** `scm_master_config.json`에서 벤더/테마 정규식 매핑과 `classification_rules.csv` 품목 매핑 로드.
  2. **원문 파싱 및 Silver 마스터 생성:**
     - `fusion_greensheet_YYYY.MM.txt` 전수 순회
     - 각 연도별 `master_YYYY.json` 및 전체 통합 `master_all.json` 파일 생성.
  3. **다중 품목 & 제조사 크로스 슬라이싱 (Gold View):**
     - 복합 품목 언급 기사를 해당 품목별 JSON(`by_category/*.json`)에 복제 배포.
     - 43개 제조사별 JSON(`by_vendor/*.json`)으로 분사.
  4. **7대 고위험 리스크 테마 슬라이싱 (`by_theme/`):**
     - `leadtime_risk.json`, `eol_tracker.json`, `price_alerts.json`, `disaster_and_accidents.json`, `geopolitics_and_tariffs.json`, `corporate_actions.json`, `high_risk_dashboard.json` 생성.
  5. **연대기 역사 타임라인 빌딩 (`by_history/`):**
     - 제조사별 타임라인(`vendor/*_history.json`) 및 품목별 타임라인(`category/*_history.json`)에 연월 순 정렬과 지능형 요약문 완착.
  6. **CLI 외장 백업 복제:** `E:\조도희\11.AI\11-07.CLI` 경로로 `master_all.json` 및 테마 뷰 자동 동기화.

---

### 3.4 `compile_scm_risk_data.py` (4대 Risk 도메인 프리컴파일러)
* **목적:** 웹 대시보드(`index.html`)의 4대 탭(조달·납기, 지정학, 경영안정, 원가·시황)에서 화면 전환 시 **지연 없는 0ms 즉시 렌더링**을 제공하기 위해 모든 정성/정량 분석 데이터를 정적 JSON으로 컴파일합니다.
* **모듈별 구성 (M1 ~ M6):**

```text
compile_scm_risk_data.py
├── [M1] compile_procurement_leadtime()
│   └── Greensheet 보고서 전수 파싱 및 마스터/슬라이스 재동기화
├── [M2] compile_geopolitics_risk()
│   ├── geopolitics_risk.json (위험 협력사 공장 위치 위경도 좌표 및 리스크 사유)
│   └── geopolitics_partners.json (지정학적 리스크 협력사 10열 정밀 비교표)
├── [M3] compile_management_stability()
│   └── stability_risk.json (경영안정 조기경보 5행, 위협요인 5행, 협력사 10열 테이블)
├── [M4] compile_cost_market_risk()
│   ├── cost_market_risk.json (원가 압박 요인, 단가 인상 요청 리스트, 원가 리스크 협력사)
│   └── 환율(USD/EUR/JPY) 연동 (Google Sheet 연동 옵션 또는 안정적 Fallback 원장)
├── [M5] compile_procurement_risk()
│   └── procurement_risk.json (리드타임 변동이력, 글로벌 공급망 병목 요인, 조달 협력사)
├── [M6] compile_ai_advisor()
│   └── ai_advisor.json (최신 1~2개월 마스터 데이터에서 추출한 실시간 조언 및 뉴스 피드)
└── [Sync] run_dual_saving_sync()
    └── CLI 백업 디렉토리(11-07.CLI)로 Gold View JSON 일괄 동기화
```

---

## 4. 스크립트 간 호출 관계 및 실행 흐름도

```
                       [ 사용자 / 개발자 ]
                                │
                      python run_pipeline.py
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
[ 1단계: compile_scm_reports.py ]     [ 2단계: compile_scm_risk_data.py ]
        │                                               │
        ├─► scm_shared.py (함수 참조)                   ├─► scm_shared.py (함수 참조)
        ├─► scm_master_config.json 로드                 ├─► scm_master_config.json 로드
        ├─► classification_rules.csv 로드               ├─► classification_rules.csv 로드
        │                                               │
        ▼                                               ▼
 [ data/master/ 생성 ]                          [ 4대 Risk 도메인 JSON 생성 ]
   - master_all.json                              - geopolitics_risk.json
   - master_YYYY.json                             - stability_risk.json
        │                                         - cost_market_risk.json
        ▼                                         - procurement_risk.json
 [ data/views/ 슬라이스 생성 ]                    - ai_advisor.json
   - by_category/*.json                                 │
   - by_vendor/*.json                                   ▼
   - by_theme/*.json                            [ data/views/ 에 저장 ]
   - by_history/vendor/*                                │
   - by_history/category/*                              ▼
        │                                  [ 외장 CLI 백업 폴더 동기화 ]
        └───────────────────────────────────────────────┘
                                │
                                ▼
                       [ index.html (SPA) ]
                 Fetch API를 통해 정적 JSON 직접 로드
                                │
                                ▼
                      [ git_push.bat 실행 ]
                                │
                                ▼
                   [ GitHub Pages 자동 배포 ]
```

---

## 5. 설정 파일 및 규칙 매핑 매커니즘

### 1) `scm_master_config.json`
* **`sheets_config`**: 구글 스프레드시트 gviz API 연동 여부(`enable_sheets_fetch`) 및 시트 ID 설정.
* **`vendor_mappings`**: 제조사 이름 정규식 패턴과 대표 표준 벤더명 매핑.
  - 예: `"pattern": "samsung|삼성|삼성전자|semco" → "representative": "Samsung"`
  - M&A 기업 통합: Altera → Intel, Xilinx → AMD, Maxim → Analog Devices
* **`theme_mappings`**: 리스크 테마 키워드 정규식 패턴.

### 2) `classification_rules.csv`
* 원문 텍스트 내 95종의 비정형 대분류 섹션 헤더를 표준 8대 품목군으로 분류하는 기준표:
  - `CPU`, `GPU`, `IC`, `Memory`, `Passive`, `PCB`, `Storage`, `Other`

---

## 6. 배포 및 운영 워크플로우

### 데이터 업데이트 시 표준 작업 순서

```powershell
# 1. 저장소 루트 디렉토리로 이동
cd "E:\조도희\01.구매기획\01-12.원재료 시황\Fusion Greensheet\my-market-intelligence"

# 2. 신규 월호 원고 추가 또는 규칙 수정 후, 통합 파이프라인 가동 (1초 완료)
python run_pipeline.py

# 3. 로컬 git 상태 확인 (정상 갱신 여부 검증)
git status

# 4. GitHub 저장소로 푸시 (배치 파일 또는 git 명령어)
git add .
git commit -m "Update SCM data lake views with latest data"
git push origin main
```

### Git Push 배치 파일(`git_push.bat`) 관련 참고
* `git_push.bat`을 실행하기 전에 **반드시 파일 수정 사항이 저장(Ctrl+S)되어 있거나, `run_pipeline.py`로 데이터가 갱신되어 `git status`에 변경 파일이 잡혀 있어야** 정상적으로 GitHub에 반영됩니다.
* 변경 사항이 없는 상태에서 실행하면 커밋할 내용이 없어 GitHub에는 새로운 변경이 발생하지 않습니다.
