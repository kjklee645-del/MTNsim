"""
4지 교차로 다중 케이스 시뮬레이션 및 궤적 데이터 저장
- 조건 1: 차량 1대
- 조건 2: 동시 차량 2~10대 (또는 경로 수까지)
- 조건 3: 모든 차량이 교차로 근처에서 시작
- 조건 4: 출력 x, y, heading, speed, acceleration

사용: python test4_trajectory_simulation.py [sumocfg]
  - test4.sumocfg (기본): 1~10대
  - SS2.sumocfg: 1~6대 (map_SS2 경로 수)
"""

import os
import sys

# SUMO traci 경로 설정
if "SUMO_HOME" in os.environ:
    sys.path.append(os.path.join(os.environ["SUMO_HOME"], "tools"))
else:
    sys.exit("SUMO_HOME 환경변수를 설정해주세요.")

import traci
import pandas as pd

# sumocfg별 경로 및 교차로 근처 departPos 설정
# (route_id, first_edge_length, departPos)
CONFIGS = {
    "test4": {
        "max_vehicles": 10,
        "routes": [
            ("r_0", 492.80, 450), ("r_1", 492.80, 450), ("r_2", 392.80, 340),
            ("r_3", 492.80, 450), ("r_4", 492.80, 450), ("r_5", 492.80, 450),
            ("r_6", 492.80, 450), ("r_7", 392.80, 340), ("r_8", 492.80, 450),
            ("r_9", 492.80, 450), ("r_10", 492.80, 450), ("r_11", 392.80, 340),
        ],
    },
    "SS2": {
        "max_vehicles": 6,
        "routes": [
            ("r_0", 60.93, 10),   # 855289482#1.82 (J1 근처)
            ("r_1", 60.93, 10),   # 855289482#1.82
            ("r_2", 32.32, 5),    # -855289482#30 (J0→7976055453)
            ("r_3", 32.32, 5),   # -855289482#30
            ("r_4", 61.78, 50),   # -855289435 (7976055454 근처)
            ("r_5", 61.78, 50),   # -855289435
        ],
    },
}


def record_trajectory_data(vehicle_data, step):
    """차량 궤적 데이터 기록: x, y, heading, speed, acceleration"""
    vehicle_ids = traci.vehicle.getIDList()
    for veh_id in vehicle_ids:
        if veh_id not in vehicle_data:
            vehicle_data[veh_id] = []
        try:
            position = traci.vehicle.getPosition(veh_id)
            speed = traci.vehicle.getSpeed(veh_id)
            acceleration = traci.vehicle.getAcceleration(veh_id)
            heading = traci.vehicle.getAngle(veh_id)
            vehicle_data[veh_id].append({
                "step": step,
                "x": position[0],
                "y": position[1],
                "heading": heading,
                "speed": speed,
                "acceleration": acceleration,
            })
        except traci.TraCIException:
            pass


def run_case(num_vehicles, sumo_cfg, route_config, output_dir, max_steps=500, use_gui=False):
    """
    특정 차량 수에 대한 시뮬레이션 실행
    모든 차량이 교차로 근처(departPos)에서 동시에 시작
    """
    sumo_binary = "sumo-gui" if use_gui else "sumo"
    sumo_cmd = [sumo_binary, "-c", sumo_cfg, "--step-length", "0.1", "--no-step-log", "--no-warnings"]
    traci.start(sumo_cmd)

    vehicle_data = {}

    # 동시에 num_vehicles대 배치 (서로 다른 경로, 교차로 근처 departPos)
    for i in range(num_vehicles):
        route_id, edge_len, depart_pos = route_config[i]
        veh_id = f"veh_{i}"
        traci.vehicle.add(veh_id, route_id, depart=0, departPos=depart_pos, departSpeed="max")

    # 시뮬레이션 수행 및 궤적 기록
    for step in range(max_steps):
        record_trajectory_data(vehicle_data, step)
        traci.simulationStep()
        if traci.simulation.getMinExpectedNumber() == 0:
            break

    traci.close()

    # DataFrame으로 변환
    records = []
    for veh_id, positions in vehicle_data.items():
        veh_idx = int(veh_id.split("_")[1])
        route_id = route_config[veh_idx][0]
        for pos in positions:
            records.append({
                "vehicle_id": veh_id,
                "route": route_id,
                "step": pos["step"],
                "x": pos["x"],
                "y": pos["y"],
                "heading": pos["heading"],
                "speed": pos["speed"],
                "acceleration": pos["acceleration"],
            })

    df = pd.DataFrame(records)
    return df


def main():
    # 작업 디렉토리를 스크립트 위치로 변경
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 인자 파싱: [sumocfg] --gui
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    use_gui = "--gui" in sys.argv or "-g" in sys.argv

    sumo_cfg = args[0] if args else "test4.sumocfg"
    config_key = "SS2" if "SS2" in sumo_cfg else "test4"
    cfg = CONFIGS[config_key]
    route_config = cfg["routes"]
    max_vehicles = cfg["max_vehicles"]

    output_subdir = "SS2" if config_key == "SS2" else "test4"
    output_dir = os.path.join(script_dir, "trajectory_output", output_subdir)
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 50)
    print("다중 케이스 궤적 시뮬레이션")
    print("=" * 50)
    print(f"설정: {sumo_cfg} (최대 {max_vehicles}대)")
    if use_gui:
        print("모드: sumo-gui (시각화)")
    else:
        print("모드: sumo (백그라운드)")

    all_summaries = []

    for n_vehicles in range(1, max_vehicles + 1):
        print(f"\n[케이스] 동시 차량 {n_vehicles}대 시뮬레이션 중...")
        try:
            df = run_case(n_vehicles, sumo_cfg, route_config, output_dir, use_gui=use_gui)
            output_file = os.path.join(output_dir, f"trajectory_veh{n_vehicles}.csv")
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            print(f"  -> 저장: {output_file} (총 {len(df)} 레코드)")

            # Excel로도 저장 (SS_test1_ver2509.py 참고)
            excel_file = os.path.join(output_dir, f"trajectory_veh{n_vehicles}.xlsx")
            df.to_excel(excel_file, index=False)
            print(f"  -> 저장: {excel_file}")

            all_summaries.append({
                "case": n_vehicles,
                "records": len(df),
                "vehicles": df["vehicle_id"].nunique(),
            })
        except Exception as e:
            print(f"  [오류] {e}")
            all_summaries.append({"case": n_vehicles, "records": 0, "vehicles": 0, "error": str(e)})

    # 요약 저장
    summary_df = pd.DataFrame(all_summaries)
    summary_path = os.path.join(output_dir, "simulation_summary.csv")
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"\n요약 저장: {summary_path}")
    print("\n완료.")


if __name__ == "__main__":
    main()
