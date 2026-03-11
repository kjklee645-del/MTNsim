# MTNsim 13단계 진행현황

작성일: 2026-03-11
기준: 초기 13단계 개발 프로세스 대비 현재 구현 수준 정리

## 1. 요약

현재 MTNsim은 13단계 기준으로 다음 수준에 도달해 있다.

- 완료: 7단계
- 부분 완료: 4단계
- 미착수: 2단계

해석하면 다음과 같다.

- 연구용 커널과 실행 구조는 상당 부분 구축됨
- 전파, 재질, calibration은 초기 실동작 단계까지 진입함
- GUI와 AI agent 실제 제어 계층은 아직 본격 착수 전임

## 2. 13단계 상태표

| 단계 | 항목 | 현재 상태 | 비고 |
| --- | --- | --- | --- |
| 1 | 제품 방향/PRD/아키텍처 | 완료 | `MTNsim_product_direction.md`, `MTNsim_PRD_draft.md`, `MTNsim_package_architecture.md` |
| 2 | manifest/schema 확정 | 완료 | `examples/project.toml`, `schemas/scenario.schema.json` 등 |
| 3 | 패키지 구조 분해 | 완료 | `src/mtnsim` 기반 패키지 구조 정리 완료 |
| 4 | SUMO 연동 + 시나리오 실행 커널 | 완료 | `sumo_adapter.py`, `run_service.py` 기반 실제 실행 가능 |
| 5 | run/result schema + 비교 서비스 | 완료 | `run.py`, `results.py`, `compare_service.py` 기반 비교 가능 |
| 6 | 전파 모듈 분리 | 완료 | `acoustics/propagation` 분리 완료 |
| 7 | 차폐 1차 버전 | 완료 | `noise_barrier`, `building footprint` 차폐 가능 |
| 8 | 지형지물 계층 명확화 | 부분 완료 | `SceneModel`, `NoiseBarrierObject`, `BuildingObject`까지 구현, terrain/vegetation 미구현 |
| 9 | 재질 기반 계산 | 부분 완료 | 재질 태그를 넘어 실제 `shielding/reflection/diffraction` 보정에 반영 중, 아직 heuristic 수준 |
| 10 | reflection/diffraction | 부분 완료 | 구조만 있는 상태를 넘어 실제 계산 경로에 연결됨, 아직 정교한 물리모델 아님 |
| 11 | calibration | 부분 완료 | 측정 CSV, 센서 메타데이터, bias/MAE/RMSE, calibration summary까지 구현 |
| 12 | GUI | 미착수 | 의도적으로 후순위 유지 |
| 13 | AI agent 실제 제어 계층 | 미착수에 가까운 부분 완료 | 아키텍처 흔적은 있으나 실제 자연어 제어 기능은 아직 없음 |

## 3. 단계별 해설

### 3.1 완료된 단계

다음 단계들은 사실상 완료로 보는 것이 맞다.

- 제품 방향/PRD/아키텍처
- manifest/schema 확정
- 패키지 구조 분해
- SUMO 연동 + 시나리오 실행 커널
- run/result schema + 비교 서비스
- 전파 모듈 분리
- 차폐 1차 버전

이 영역은 현재 코드와 문서 체계가 안정화되어 있고, 실제 실행 및 비교 검증도 이루어졌다.

### 3.2 부분 완료 단계

#### 지형지물 계층 명확화
현재는 `noise_barriers`, `buildings` 중심으로 runtime object 계층이 존재한다. 하지만 전문 툴 수준으로 가기 위해서는 `terrain surface`, `terrain edge`, `ground type`, `vegetation` 계층이 추가되어야 한다.

#### 재질 기반 계산
현재는 재질이 단순 태그가 아니라 실제 전파 계산에 반영된다. 다만 계산 방식은 heuristic 중심이며, 재질 라이브러리와 물리 파라미터 체계는 더 정교해져야 한다.

#### reflection/diffraction
현재는 `specular single-bounce reflection`, `path-excess diffraction` 기반의 1차 모델이 작동한다. 즉 미구현 상태는 지났지만, 상용 해석 수준의 물리 정밀도와는 아직 거리가 있다.

#### calibration
현재는 측정 CSV와 센서 메타데이터를 읽어 receiver 매핑, time offset, bias/MAE/RMSE, global offset recommendation을 계산할 수 있다. 그러나 자동 시간동기화, 위치 오차 보정, 이상치 제거, 실측 기반 validation 체계는 아직 남아 있다.

### 3.3 미착수 단계

#### GUI
현재는 CLI와 설정 파일 중심의 엔진 단계다. GUI는 아직 만들지 않았고, 의도적으로 후순위로 두고 있다.

#### AI agent 실제 제어 계층
초기 아키텍처에서는 향후 자연어 기반 제어를 고려해 구조를 잡아두었지만, 실제로 자연어를 받아 scenario 수정, 실행 승인, 결과 설명, audit/replay를 수행하는 에이전트 계층은 아직 구현되지 않았다.

## 4. 현재 위치의 의미

현재 MTNsim은 단일 프로토타입 스크립트 수준을 벗어나서, 다음 수준에 도달해 있다.

- 재현 가능한 미시 교통소음 실행 커널
- 시나리오 비교 가능한 연구 플랫폼
- 장면 객체와 재질 속성을 다룰 수 있는 초기 전파 엔진
- 측정값과 비교 가능한 초기 calibration 루프

즉, 이제부터의 핵심 과제는 "구조 만들기"보다 "정확도와 검증력 올리기"에 가깝다.

## 5. 다음 우선순위

현재 기준 다음 우선순위는 아래 순서가 맞다.

1. `reflection/diffraction` 물리모델 정교화
2. `material-aware correction` 고도화
3. `calibration` 정교화
4. `GUI` 구축
5. `AI agent 실제 제어 계층` 구축

## 6. 결론

13단계 기준으로 보면, MTNsim은 이미 초반 기반 공사 단계는 지나갔다. 현재는 중반부에 진입해 있으며, 완성도를 결정하는 핵심 구간은 전파 정확도와 calibration 품질이다. 따라서 앞으로의 개발은 GUI나 외형보다, 물리모델 정교화와 검증 체계 강화에 집중하는 것이 맞다.