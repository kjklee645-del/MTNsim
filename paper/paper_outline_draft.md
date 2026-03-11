# MTNsim 논문 초안 패키지

작성일: 2026-03-10
문서 목적: 논문 집필을 바로 시작할 수 있도록 목차, 초록, 그림/표 목록을 1차 초안으로 정리한다.

## 1. 제목 후보

### 국문 제목 후보

1. 개별 차량 궤적 기반 미시 교통소음 시뮬레이션 프레임워크 개발
2. 차량 이동 궤적과 장면 객체를 반영한 미시적 도로교통 소음 예측 모델
3. 지형지물 및 차량 이벤트를 고려한 미시 교통소음 시뮬레이션 방법론

### 영문 제목 후보

1. Development of a Microscopic Traffic Noise Simulation Framework Based on Vehicle-Level Trajectories
2. A Microscopic Road Traffic Noise Simulation Model with Vehicle Trajectories and Scene Objects
3. A Scene-Aware Microscopic Traffic Noise Simulation Framework for Vehicle-Level Noise Analysis

## 2. 논문 목차 초안

### 1. 서론
- 교통소음 평가의 필요성
- 기존 평균 교통량 기반 평가의 한계
- 미시 교통 시뮬레이션 기반 접근의 필요성
- 본 연구의 목적과 기여

### 2. 관련 연구
- 도로교통 소음 예측의 기존 방법
- 미시 교통 시뮬레이션과 소음모델 연계 연구
- 장면 객체 및 지형지물 반영 연구
- 기존 연구 대비 본 연구의 차별점

### 3. MTNsim 프레임워크
- 전체 시스템 구조
- project manifest 및 scenario 기반 구성
- SUMO 연동 구조
- 차량별 방사소음 계산 구조
- 전파 계산 모듈(distance, shielding, reflection, diffraction)
- receiver/grid 결과 생성 구조

### 4. 장면 객체 및 전파 보정 모델
- noise barrier와 building 객체 정의
- scene runtime object 계층
- 공통 propagation property 구조
- material-aware correction 개념
- 1차 reflection/diffraction heuristic 모델

### 5. 실험 설계
- 실험 네트워크와 기본 조건
- baseline 시나리오 정의
- speed_drop_80 시나리오 정의
- lane_change_enforce 시나리오 정의
- barrier_shielding 시나리오 정의
- building_shielding_default 및 building_shielding 정의
- 평가 지표

### 6. 실험 결과
- 속도 제어 효과 분석
- 차로 변경 제어 효과 분석
- 방음벽 차폐 효과 분석
- 건물 차폐 효과 분석
- material-aware propagation 영향 분석
- 수음점별 평균 및 시계열 변화 해석

### 7. 논의
- 프레임워크의 활용 가능성
- 현재 모델의 한계
- SoundPLAN류 전문 툴로 확장하기 위한 과제
- 실측 calibration 및 validation 필요성

### 8. 결론
- 연구 요약
- 핵심 기여 정리
- 향후 연구 방향

## 3. 초록 초안

본 연구는 개별 차량 수준의 이동 궤적과 도로변 장면 객체를 반영하여 교통소음을 시간축에서 재현할 수 있는 미시 교통소음 시뮬레이션 프레임워크인 MTNsim을 제안한다. 기존의 도로교통 소음평가는 주로 평균 교통량 또는 정적인 조건을 기반으로 수행되어 속도 변화, 차로 변경, 이벤트성 차량 거동, 그리고 국부적인 차폐물의 영향을 세밀하게 반영하는 데 한계가 있다. 이를 개선하기 위해 본 연구에서는 SUMO 기반의 미시 교통 시뮬레이션과 차량별 방사소음 계산, 수음점 및 격자 기반 소음장 계산, 그리고 방음벽 및 건물 객체를 고려한 전파 보정 구조를 통합한 시뮬레이션 프레임워크를 구현하였다. 또한 장면 객체별 재질 및 전파 속성을 반영할 수 있는 구조를 도입하고, 1차 수준의 shielding, reflection, diffraction heuristic을 전파 계산 경로에 연결하였다. 제안한 프레임워크를 이용하여 속도 제어, 차로 변경 제어, 방음벽 차폐, 건물 차폐, 재질 속성 변화 시나리오를 비교한 결과, 속도 저감 시 평균 소음도 감소, 차폐물 배치에 따른 유의미한 수음점 소음 저감, 그리고 재질 속성 변화에 따른 근거리 및 원거리 수음점의 차등 효과를 확인하였다. 본 연구는 실측 기반 검증이 완료된 상용 해석모델을 제시하는 단계는 아니지만, 향후 calibration과 3차원 전파모델 확장을 통해 전문 교통소음 시뮬레이션 도구로 발전할 수 있는 구조적 기반을 제시한다.

## 4. 연구 기여 항목 초안

1. 개별 차량 궤적 기반의 미시 교통소음 시뮬레이션 프레임워크를 제안하였다.
2. 장면 객체와 재질 속성을 반영할 수 있는 모듈형 전파 구조를 구현하였다.
3. 다양한 교통 운영 및 차폐 시나리오를 재현 가능한 설정 구조로 비교할 수 있도록 하였다.

## 5. 그림 목록 초안

### Figure 1
MTNsim 전체 시스템 아키텍처
내용:
- 입력 계층
- SUMO 기반 교통엔진
- 방사소음 모듈
- 전파 모듈
- 결과 저장 및 비교 모듈

### Figure 2
시나리오 실행 및 데이터 흐름도
내용:
- project manifest
- scenario config
- run service
- receiver/grid output
- comparison service

### Figure 3
실험 네트워크 및 수음점 배치도
내용:
- 4lane 네트워크
- receivers 위치
- barrier/building 위치

### Figure 4
baseline과 speed_drop_80의 receiver 평균 소음도 비교 그래프
내용:
- 수음점별 평균 dB 비교 막대그래프

### Figure 5
baseline과 barrier_shielding의 receiver 평균 소음도 비교 그래프
내용:
- 차폐 효과 강조

### Figure 6
building_shielding_default와 building_shielding의 receiver별 평균 변화 그래프
내용:
- 재질 속성 및 반사 효과 비교

### Figure 7
대표 시나리오의 grid noise snapshot heatmap
내용:
- baseline
- barrier_shielding 또는 building_shielding

### Figure 8
대표 receiver의 시간 이력 그래프
내용:
- baseline 대비 scenario별 timeseries

## 6. 표 목록 초안

### Table 1
시나리오별 입력 변수 비교
열 예시:
- Scenario
- Speed control
- Lane change mode
- Barrier
- Building
- Material override

### Table 2
주요 파라미터 및 기본 설정
열 예시:
- Parameter
- Value
- Description

### Table 3
시나리오별 receiver 평균 소음도 변화 요약
열 예시:
- Comparison
- Mean of mean dB delta
- Largest decrease receiver
- Largest increase receiver

### Table 4
장면 객체별 propagation property 예시
열 예시:
- Object type
- Material
- Shielding attenuation
- Reflection loss
- Diffraction loss
- Absorption coefficient

## 7. 바로 이어서 해야 할 작업

1. Figure 3에 들어갈 네트워크 및 수음점 배치 그림 생성
2. Table 1, Table 3에 들어갈 실험 결과 수치 정리
3. Figure 4~8용 데이터 추출 스크립트 작성
4. 초록을 투고 학회 양식에 맞게 분량 조정
5. 서론 첫 2개 문단 초안 작성