# 🎛️ SCM 시황 데이터 레이크 AI 가이드라인 & 자동화 개발계획서 (GEMINI.md)

이 파일은 SCM Risk 대시보드 및 시황 데이터 레이크(`my-market-intelligence`)의 데이터 가공, 분류, 그리고 정합성 유지 관리를 위한 **AI 및 개발자 지침서**입니다. 이 저장소를 물려받는 미래의 제미나이(Gemini)나 개발자는 이 문서의 지침을 100% 우선순위로 준수해야 합니다.

---

## 📂 1. 디렉토리 구조 (Directory Structure)

이 저장소는 SCM 시황 추적을 위해 **Bronze-Silver-Gold Medallion 아키텍처**로 완착되어 있습니다.

```directory
my-market-intelligence/
├── GEMINI.md                    # [본 파일] AI 및 개발 지침서
├── classification_rules.csv     # 품목군 분류 표준화 엑셀 매핑 규칙 원본
├── compile_scm_reports.py       # [마스터 빌더] 전수 가공 및 리빌드 자동화 엔진
├── data/
│   ├── raw/                     # [Bronze] 70개 월분 정제 마크다운 원고 (.md)
│   ├── master/                  # [Silver] 정형 통합 마스터 원장 (.json)
│   └── views/                   # [Gold] SCM 대시보드 실시간 연동용 슬라이스 API
│       ├── by_category/         # 8대 품목군별 교차 분사 뷰팩
│       ├── by_vendor/           # 43사 제조사별 슬라이스 뷰팩
│       ├── by_theme/            # 7대 고위험 리스크 테마별 뷰팩
│       └── by_history/          # 7개년 연대기적 SCM 역사 타임라인 JSON
│           ├── category/        # 품목군별 타임라인 역사 사전
│           └── vendor/          # 제조사별 타임라인 역사 사전
```

---

## ⚙️ 2. 데이터 레이크 1초 자동 가동 엔진 (`compile_scm_reports.py`)

로컬 PC에서 원문 보고서(.txt)를 정비하거나, 신규 월호 원고를 추가하거나, `classification_rules.csv`의 분류 매핑을 바꾼 뒤 **복잡한 인공지능 프롬프트 지시 없이 단 한 줄의 명령어로 데이터 전체를 동기화 리빌드**할 수 있도록 마스터 스크립트가 탑재되어 있습니다.

```powershell
# 1. 저장소 폴더로 이동
cd "E:\조도희\01.구매기획\01-12.원재료 시황\Fusion Greensheet\my-market-intelligence"

# 2. 마스터 빌더 스크립트 실행 (끝!)
python compile_scm_reports.py
```

### 🛠️ 마스터 빌더가 수행하는 5단계 자동 공정:
1.  **원고 가공 (Bronze 정제):** 원문 파일 속 꼬리말 노이즈 소거 및 분절 단락 병합 가공 처리.
2.  **분류 바인딩 (Silver 정형):** `classification_rules.csv`를 읽어와 95종 원문 대분류 명칭을 **8대 정규 품목군**으로 매핑.
3.  **다중 품목 매핑 & 크로스 슬라이싱 (Gold 복제):** 복합 주제 뉴스(561건)를 감측하여 여러 품목 뷰팩에 중복 복제 적재.
4.  **역사 타임라인 빌딩 (Gold Chronological):** 43사 제조사 및 8대 품목의 7개년 역사를 시간 순서대로 정렬하고, 첫 문장/헤더 기반 **80자 지능형 요약**을 수행하여 타임라인 JSON 완착.
5.  **동기화 백업:** 외장 백업 드라이브(`E:\조도희\11.AI\11-07.CLI\`)로 최종 마스터 원장 자동 카피.

---

## 🤖 3. 미래의 AI 어시스턴트(Gemini/Claude 등)를 위한 지시 가이드

향후 새로운 AI에게 작업을 지시할 때는, 이 `GEMINI.md`와 아래의 프롬프트 서식을 복사해서 주면 AI가 즉시 프로젝트를 100% 이해하고 오동작 없이 기계적으로 완벽하게 작업합니다.

### 💡 [AI 프롬프트 표준 서식]
> "너는 내 SCM 데이터 엔지니어 파트너이다. 내 로컬 저장소에 있는 `GEMINI.md`를 먼저 정독해서 이 프로젝트의 디렉토리 아키텍처와 작동 원리를 파악해라.
> 
> [이번에 내가 정비한 사항]
> - 예시: `data/raw/` 폴더에 2026년 9월호 원고(`monthly/2026_09.md` 및 `fusion_greensheet_2026.09.txt`)를 추가했다.
> - 예시: `classification_rules.csv` 엑셀 파일 d열에 신규 벤더/품목 매핑 규칙을 3개 추가했다.
> 
> [너의 미션]
> 1. `compile_scm_reports.py` 마스터 빌더를 가동하여, 추가/수정된 사항을 기반으로 전체 데이터 레이크 JSON 뷰팩 및 연대기 역사 타임라인을 재생성해라.
> 2. 리빌드가 완수되면, git status를 확인하여 정상 갱신되었는지 보고하고 깃 커밋을 만들어라."

---

## 🌟 SCM 인텔리전스 데이터 무결성 규칙 (Data Integrity Rules)
*   **소문자 오탐지 절대 가드:** TI, ADI 등 소형 벤더명은 무조건 대소문자를 엄격히 가리는 **대문자 독립 낱말 정규식(`\bTI\b`)**으로만 매치해야 합니다. (Tier, Edition 등으로 오탐지하는 것 절대 차단)
*   **M&A 표준 수렴:** Altera는 Intel로, Xilinx는 Amd로, Maxim은 Analog Devices로, NXP는 Nexperia로 자동 병합되어야 합니다.
*   **Onsemi 다변 표기 대응:** `On Semi`, `On-Semi`, `On_Semi`, `onsemi` 등은 모두 `"Onsemi"` 단일 브랜드로 수동 융합되어야 합니다.

이 문서와 마스터 파이프라인 엔진은 SCM 데이터 자산의 지속 가능한 자동화를 영구 보장합니다.
