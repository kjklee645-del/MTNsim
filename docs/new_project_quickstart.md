# New Project Quickstart

이 문서는 MTNsim GUI에서 `새 프로젝트 생성 -> SUMO 연결 -> 첫 실행`까지 가장 짧은 경로만 정리합니다.

## 1. GUI 실행

```powershell
cd D:\Codex\MTNsim
$env:PYTHONPATH='D:\Codex\MTNsim\src'
& 'C:\Users\user\miniconda3\envs\Trac\python.exe' -m mtnsim.app.main --gui
```

## 2. 새 프로젝트 만들기

### 방법 A. 기존 SUMO 프로젝트를 바로 가져오기

1. 상단 메뉴에서 `Import SUMO Project`를 누릅니다.
2. 아래 값을 입력합니다.
   - `Project name`: 새 MTNsim 프로젝트 이름
   - `Description`: 설명
   - `Default scenario`: 보통 `baseline`
   - `Project folder`: 새 프로젝트가 만들어질 폴더
   - `SUMO config (.sumocfg)`: 가져올 SUMO 설정 파일
3. 필요하면 아래 옵션을 고릅니다.
   - `Copy SUMO files into the project`
   - `Allow overwrite if manifest/scenario already exist`
   - `Scene file (optional)`
   - `Measurements file (optional)`
   - `Measurement metadata (optional)`
4. `Inspect SUMO Files`를 눌러 파일 검사를 실행합니다.
5. 요약창에 blocking issue가 없으면 `Import Project`를 누릅니다.

### 방법 B. 빈 프로젝트를 먼저 만들기

1. 상단 메뉴에서 `New Project`를 누릅니다.
2. `Attach SUMO config now`를 끄면 빈 프로젝트를 만들 수 있습니다.
3. 프로젝트가 열린 뒤 나중에 `Attach SUMO`로 `.sumocfg`를 연결합니다.

## 3. 프로젝트가 정상 생성됐는지 확인

프로젝트가 열리면 `Project Home`에서 아래를 확인합니다.
- `Project:` 이름 표시
- `Status:` 상태 표시
- `Available Scenarios` 목록 표시

SUMO가 제대로 연결된 프로젝트라면 보통 `ready to run` 상태가 보입니다.

## 4. 시나리오 편집

1. 좌측 메뉴에서 `Scenario Editor`를 엽니다.
2. 먼저 아래 항목만 바꿔도 충분합니다.
   - `Max vehicles`
   - `Start speed (km/h)`
   - `Vehicle interval (s)`
   - `Post target speed (km/h)`
   - `Background noise (dB)`
   - receiver table (`ID / X / Y / Z`)
3. 저장은 원본 덮어쓰기가 아니라 `Save As New Scenario`로 새 시나리오를 만드는 방식이 안전합니다.

참고 문서:
- [scenario_editor_field_reference.md](D:/Codex/MTNsim/docs/scenario_editor_field_reference.md)

## 5. 장면 확인

1. `Scene View`를 엽니다.
2. 도로, receiver, barrier/building/terrain 등이 2D로 보이는지 확인합니다.
3. receiver 위치를 바꾸면 저장 전에도 preview가 즉시 반영됩니다.

## 6. 첫 시뮬레이션 실행

1. 실행할 시나리오를 선택합니다.
2. 상단의 `Run Selected` 또는 `Run Selected Scenario`를 누릅니다.
3. `Run Monitor`에서 아래를 확인합니다.
   - project
   - scenario
   - progress
   - GPU used 여부
4. 완료되면 `Open Result Viewer`로 이동합니다.

## 7. 결과 보기

### Result Viewer
- receiver 통계 테이블
- receiver 시계열 그래프
- output folder / summary / manifest 바로 열기
- Markdown summary export

### Vehicle Playback
- 차량 이동 재생
- heatmap 오버레이
- receiver 커서 연동
- 선택 차량 기여도
- PNG / GIF / MP4 export

### Compare
- 시나리오 A/B 설정 차이
- `Run and Compare`
- receiver delta table
- 선택 receiver overlay chart

## 8. 빈 프로젝트에 나중에 SUMO 붙이기

1. 프로젝트를 연 상태에서 상단 `Attach SUMO`를 누릅니다.
2. `.sumocfg`를 선택합니다.
3. 필요하면 attach 옵션을 고릅니다.
   - selected scenario only / all scenarios
   - update traffic metadata
   - rebuild vehicle coefficients
   - replace placeholder receivers
   - update lane-change targets
4. `Attach SUMO`를 누릅니다.
5. 프로젝트가 다시 로드되고 `Run`이 활성화되는지 확인합니다.

## 9. 자주 생기는 문제

### `SUMO config does not contain an <input> section`
최근 버전에서는 top-level `net-file`, `route-files` 형식도 지원합니다.
이 메시지가 다시 나오면 GUI를 완전히 재시작한 뒤 다시 시도합니다.

### `Run` 버튼이 비활성화됨
보통 아래 중 하나입니다.
- SUMO가 아직 연결되지 않음
- 프로젝트가 빈 프로젝트 상태임
- 시나리오가 선택되지 않음

### Import 후 아무 반응이 없음
검사 실패나 missing file이 있을 수 있습니다.
다이얼로그 아래 summary를 확인하고, 경고창이 뜨면 그 메시지를 먼저 해결합니다.

## 10. 추천 첫 실습 흐름

1. `Import SUMO Project`
2. `Inspect SUMO Files`
3. `Import Project`
4. `Scene View`에서 receiver 위치 확인
5. `Scenario Editor`에서 속도/차량 수 수정
6. `Save As New Scenario`
7. `Run Selected`
8. `Result Viewer`와 `Vehicle Playback` 확인
9. 필요하면 `Compare`로 baseline과 비교

## 관련 문서
- [README.md](D:/Codex/MTNsim/README.md)
- [user_guide.md](D:/Codex/MTNsim/docs/user_guide.md)
- [gui_mvp_plan.md](D:/Codex/MTNsim/docs/gui_mvp_plan.md)
- [new_project_import_ux_plan.md](D:/Codex/MTNsim/docs/new_project_import_ux_plan.md)
