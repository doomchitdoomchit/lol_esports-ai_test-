# lol Esports(gemini)

LCK(League of Legends Champions Korea) e스포츠 데이터 분석 대시보드 프로젝트입니다. Streamlit을 활용하여 선수 및 팀의 성과 지표, 스타일 분석, 챔피언 통계 등을 시각화하여 제공합니다.

## 주요 기능 (Features)

이 프로젝트는 다음과 같은 분석 페이지를 제공합니다:

1.  **Home (`Home.py`)**
    *   대시보드의 메인 페이지로, 전체적인 데이터셋 개요를 확인하고 사이드바를 통해 글로벌 필터(연도, 시즌, 플레이오프 여부, 패치 버전)를 설정할 수 있습니다.

2.  **EDA (`pages/1_EDA.py`)**
    *   **Champion Analysis**: 팀 데이터를 기반으로 챔피언 픽/밴/승률/패배율을 분석합니다.
    *   **Game Analysis**: 진영별 승률(Blue vs Red), 게임 시간 분포, 첫 오브젝트 획득 시 승률 등을 시각화합니다.

3.  **Champion Stats (`pages/2_Champion_Stats.py`)**
    *   챔피언별 상세 통계(Pick%, Ban%, Win%, P+B%)를 테이블 형태로 제공합니다.
    *   포지션별 필터링 및 정렬 기능을 지원합니다.

4.  **Player Profile (`pages/3_Player_Profile.py`)**
    *   선수 개인의 상세 프로필 및 성과 지표(KDA, DPM, GPM 등)를 조회합니다.
    *   **Player Style Analysis**: 8가지 요인(Factor) 기반의 레이더 차트를 통해 선수의 플레이 스타일을 분석합니다.
    *   **Most 5 Champions**: 선수가 주로 사용하는 상위 5개 챔피언의 상세 성적을 보여줍니다.

5.  **Team Profile (`pages/4_Team_Profile.py`)**
    *   팀 단위의 성과 지표 및 리그 평균과의 비교 분석을 제공합니다.
    *   **Performance Radar**: 리그 평균 대비 팀의 주요 지표(KDA, DPM, GPM, VSPM)를 레이더 차트로 비교합니다.
    *   **Laning Phase**: 시간대별(10~25분) 골드 및 CS 격차를 시각화합니다.
    *   **Object Control**: 오브젝트(드래곤, 바론, 전령 등) 획득에 따른 승률을 분석합니다.

6.  **Player Comparison (`pages/5_Player_Comparison.py`)**
    *   두 선수를 선택하여 1:1로 비교 분석합니다.
    *   **Style Comparison**: 두 선수의 플레이 스타일을 겹쳐진 레이더 차트와 차이 그래프로 비교합니다.
    *   **Head-to-Head**: 두 선수의 맞대결 전적 및 상세 기록을 조회합니다.

## 데이터 (Data)

본 프로젝트는 `data/` 디렉토리에 위치한 다음 CSV 파일들을 사용합니다:

*   **`lck.csv`** ([출처: Oracle's Elixir](https://oracleselixir.com/))
    *   LCK 경기 데이터가 포함된 메인 데이터셋입니다.
    *   단일 CSV 파일 내에 선수(Player) 데이터와 팀(Team) 데이터가 혼재되어 있어, `components/data_loader.py`에서 이를 분리하여 로드합니다.

*   **`cluster.csv`**
    *   Scikit-learn의 Hierarchical Clustering을 사용하여 생성된 클러스터링 결과입니다.
    *   Distance가 elbow point인 지점을 기준으로 클러스터 개수를 정의하였습니다.

*   **`val.csv`**
    *   `factor_analyzer` 패키지의 FactorAnalyzer를 사용하여 도출된 요인 분석 데이터입니다.
    *   Cumulative Variance > 0.6 (60%) 일 때를 기준으로 요인(Factor) 개수를 정의하였습니다.
    *   Player Profile 및 Comparison 페이지의 스타일 분석에 활용됩니다.

## 설치 및 실행 (Installation & Usage)

### 요구 사항 (Requirements)
*   Python 3.8+
*   Streamlit
*   Pandas
*   Plotly
*   Scikit-learn
*   Factor-analyzer

### 실행 방법 (Run)
프로젝트 루트 디렉토리에서 다음 명령어를 실행합니다:

```bash
streamlit run Home.py
```

## 프로젝트 구조 (Project Structure)

```
lol Esports(gemini)/
├── Home.py                 # 메인 애플리케이션 진입점
├── components/             # 재사용 가능한 컴포넌트 및 유틸리티
│   ├── data_loader.py      # 데이터 로딩 및 전처리
│   ├── sidebar.py          # 사이드바 필터 컴포넌트
│   ├── charts.py           # 차트 생성 함수
│   └── utils.py            # 공통 유틸리티 함수 (필터링 등)
├── pages/                  # Streamlit 페이지
│   ├── 1_EDA.py
│   ├── 2_Champion_Stats.py
│   ├── 3_Player_Profile.py
│   ├── 4_Team_Profile.py
│   └── 5_Player_Comparison.py
├── data/                   # 데이터 파일 (lck.csv, val.csv 등)
└── README.md               # 프로젝트 문서
```