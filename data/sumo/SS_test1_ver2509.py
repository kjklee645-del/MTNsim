import traci
import random
import time
import math
import pandas as pd
import xml.etree.ElementTree as ET





def get_detector_lanes(detector_file):
    tree = ET.parse(detector_file)
    root = tree.getroot()
    detector_lanes = {}
    for detector in root.findall('inductionLoop'):
        detector_lanes[detector.get('id')] = detector.get('lane')
    return detector_lanes



def generate_vehicles(vehicle_counter, total_vehicles, routes, weights, step):
    if vehicle_counter < total_vehicles:
        if random.uniform(0, 1) < 0.1:
            route_id = random.choices(population=routes, weights=weights, k=1)[0]
            traci.vehicle.add(f"veh{vehicle_counter}", route_id, depart=step, departSpeed="max")
            vehicle_counter += 1
    return vehicle_counter


# ?�정??generate_vehicles ?�수 (?�용?��? weights�??�력?????�도�?변�?
def generate_vehicles2(vehicle_counter, total_vehicles, routes, weights, step, vehicle_speed, vehicle_start_interval, min_gap):
    """
    차량???�정 간격?�로 ?�성?�고, ?�속 ?�동???��??�도�??�정.

    :param vehicle_counter: ?�재 ?�성??차량 ??
    :param total_vehicles: ?�성??�?차량 ??
    :param routes: ?�용 가?�한 경로 리스??
    :param weights: ?�용?��? 직접 ?�정??경로�??�률 (routes?� 길이가 같아????
    :param step: ?�재 ?��??�이???�텝
    :param vehicle_speed: 차량???�속?�동 ?�도
    :param vehicle_start_interval: 차량 출발 간격
    :param min_gap: 차량 �?최소 거리
    :return: ?�데?�트??vehicle_counter
    """
    if vehicle_counter < total_vehicles:
        if step % vehicle_start_interval == 0:   # 일정 간격마다 차량 생성
            if len(routes) != len(weights):
                raise ValueError("routes 리스?��? weights 리스?�의 길이가 같아???�니??")

            route_id = random.choices(population=routes, weights=weights, k=1)[0]
            veh_id = f"veh{vehicle_counter}"

            # 해당 경로의 첫 번째 차선 ID 가져오기
            first_edge = traci.route.getEdges(route_id)[0] # 첫 번째 경로 엣지
            lane_id = f"{first_edge}_0"  # 첫 번째 차선


             # 이전 차량과의 거리 확인 후 생성
            if traci.lane.getLastStepVehicleNumber(lane_id) == 0 or \
               traci.lane.getLastStepLength(lane_id) > min_gap:
                
                traci.vehicle.add(veh_id, route_id, depart=step, departSpeed=str(vehicle_speed))
                traci.vehicle.setMaxSpeed(veh_id, vehicle_speed)  # 최대 속도를 명확하게 설정
                traci.vehicle.setSpeed(veh_id, vehicle_speed)  # 속도 고정
                traci.vehicle.setAccel(veh_id, 0)  # 가속도 0 (등속 운동)
                traci.vehicle.setSpeedMode(veh_id, 0)  # SUMO의 속도 자동 조정 해제

                vehicle_counter += 1

    return vehicle_counter



def record_vehicle_data(vehicle_data, step, detector_lanes):
    vehicle_ids = traci.vehicle.getIDList()
    for veh_id in vehicle_ids:
        if veh_id not in vehicle_data:
            vehicle_data[veh_id] = {
                "id": veh_id,
                "route": traci.vehicle.getRouteID(veh_id),
                "departure": step,
                "arrival": -1,
                "positions": [],
                "detectors": []
            }
        if traci.vehicle.isStopped(veh_id) and vehicle_data[veh_id]["arrival"] == -1:
            vehicle_data[veh_id]["arrival"] = step

        position = traci.vehicle.getPosition(veh_id)
        speed = traci.vehicle.getSpeed(veh_id)
        acceleration = traci.vehicle.getAcceleration(veh_id)
        heading = traci.vehicle.getAngle(veh_id)
        speed_x = speed * traci.vehicle.getLateralLanePosition(veh_id)
        speed_y = speed * traci.vehicle.getLanePosition(veh_id)
        
        vehicle_data[veh_id]["positions"].append({
            "step": step,
            "position": position,
            "speed": speed,
            "acceleration": acceleration,
            "heading": heading,
            "speed_x": speed_x,
            "speed_y": speed_y,
            "detector": 0
        })
        
        lane_id = traci.vehicle.getLaneID(veh_id)
        for detector_id, detector_lane in detector_lanes.items():
            if lane_id == detector_lane and not any(d["step"] == step and d["detector_id"] == detector_id for d in vehicle_data[veh_id]["detectors"]):
                vehicle_data[veh_id]["detectors"].append({
                    "detector_id": detector_id,
                    "step": step
                })
                for pos in vehicle_data[veh_id]["positions"]:
                    if pos["step"] == step:
                        pos["detector"] = 1






def _make_sheet_name(base_name, suffix=None):
    invalid_chars = ['[', ']', ':', '*', '?', '/', '\\']
    base = str(base_name).strip()
    if not base:
        base = "Sheet"
    for ch in invalid_chars:
        base = base.replace(ch, '_')
    suffix_str = f"_{suffix}" if suffix is not None else ""
    max_len = 31
    if len(base + suffix_str) > max_len:
        allowed_base_len = max_len - len(suffix_str)
        if allowed_base_len < 1:
            allowed_base_len = 1
        base = base[:allowed_base_len]
    return f"{base}{suffix_str}"


def write_dataframe_in_chunks(writer, df, base_sheet_name, max_rows=1048576):
    """Split DataFrame across multiple sheets to respect Excel row limits."""
    if df.empty:
        df.to_excel(writer, sheet_name=_make_sheet_name(base_sheet_name), index=False)
        return
    total_rows = len(df)
    if total_rows <= max_rows:
        df.to_excel(writer, sheet_name=_make_sheet_name(base_sheet_name), index=False)
        return
    chunk_count = math.ceil(total_rows / max_rows)
    for chunk_idx in range(chunk_count):
        start = chunk_idx * max_rows
        end = min(start + max_rows, total_rows)
        sheet_name = _make_sheet_name(base_sheet_name, chunk_idx + 1)
        df.iloc[start:end].to_excel(writer, sheet_name=sheet_name, index=False)


def save_vehicle_records_to_excel(vehicle_data, filename="vehicle_records_0929_ttt.xlsx"):
    records = []
    detector_records = {}

    for record in vehicle_data.values():
        for pos in record["positions"]:
            records.append({
                "Vehicle ID": record["id"],
                "Route": record["route"],
                "Departure": record["departure"],
                "Arrival": record["arrival"],
                "Step": pos["step"],
                "Position X": pos["position"][0],
                "Position Y": pos["position"][1],
                "Speed": pos["speed"],
                "Acceleration": pos["acceleration"],
                "Heading": pos["heading"],
                "Speed X": pos["speed_x"],
                "Speed Y": pos["speed_y"],
                "Detector": pos["detector"]
            })
        for detector in record["detectors"]:
            detector_records.setdefault(detector["detector_id"], []).append({
                "Vehicle ID": record["id"],
                "Route": record["route"],
                "Departure": record["departure"],
                "Arrival": record["arrival"],
                "Step": detector["step"]
            })

    df = pd.DataFrame(records)
    with pd.ExcelWriter(filename) as writer:
        write_dataframe_in_chunks(writer, df, "All Records")
        for detector_id in sorted(detector_records):
            df_detector = pd.DataFrame(detector_records[detector_id])
            write_dataframe_in_chunks(writer, df_detector, f"Detector {detector_id}")

def main():
    sumoBinary = "sumo"
    #sumoBinary = "sumo-gui"

    sumoCmd = [sumoBinary, "-c", "SS2_100ms_ttt.sumocfg"]

    traci.start(sumoCmd)

    routes = ["r_0", "r_1", "r_2", "r_3", "r_4", "r_5", "r_6"]
    weights = [0.2, 0.1, 0.2, 0.1, 0.2, 0.1, 0.1]  # 사용자 지정 확률
    #routes = ["r_2","r_3", "r_6"]
    #weights = [0.1, 0.4, 0.5]  # 사용자 지정 확률

    total_vehicles = 10000
    vehicle_data = {}
    detector_lanes = get_detector_lanes("map_SS2_detector.xml")

    vehicle_counter = 0
    vehicle_speed = 8.33  # 모든 차량이 유지할 속도 (m/s, 30km/h)
    vehicle_start_interval = 10   # 차량 출발 간격 (시뮬레이션 스텝 기준)
    min_gap = 10  # 차량 간 최소 거리(m)


    for step in range(300000):
        vehicle_counter = generate_vehicles(vehicle_counter, total_vehicles, routes, weights, step)
        #vehicle_counter = generate_vehicles2(vehicle_counter, total_vehicles, routes, weights, step, vehicle_speed, vehicle_start_interval, min_gap)

        record_vehicle_data(vehicle_data, step, detector_lanes)
        traci.simulationStep()
        time.sleep(0.01)

    save_vehicle_records_to_excel(vehicle_data)
    traci.close()

if __name__ == "__main__":
    main()




