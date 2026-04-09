from __future__ import annotations

from dataclasses import asdict

from mtnsim.schemas.results import ReceiverDelta, RunResultComparison, RunResultSummary, ScenarioComparison
from mtnsim.schemas.scenario import ScenarioConfig


class CompareService:
    def compare_scenarios(self, scenario_a: ScenarioConfig, scenario_b: ScenarioConfig) -> ScenarioComparison:
        if scenario_a.scenario.project != scenario_b.scenario.project:
            project_name = f"{scenario_a.scenario.project} vs {scenario_b.scenario.project}"
        else:
            project_name = scenario_a.scenario.project

        a_fields = self._flatten_scenario(scenario_a)
        b_fields = self._flatten_scenario(scenario_b)
        differing_fields: dict[str, dict[str, object]] = {}
        for key in sorted(set(a_fields) | set(b_fields)):
            if a_fields.get(key) != b_fields.get(key):
                differing_fields[key] = {
                    'scenario_a': a_fields.get(key),
                    'scenario_b': b_fields.get(key),
                }

        return ScenarioComparison(
            project=project_name,
            scenario_a=scenario_a.scenario.name,
            scenario_b=scenario_b.scenario.name,
            differing_fields=differing_fields,
        )

    def compare_run_results(self, result_a: RunResultSummary, result_b: RunResultSummary) -> RunResultComparison:
        receiver_ids = sorted(set(result_a.receiver_stats) | set(result_b.receiver_stats))
        receiver_deltas: dict[str, ReceiverDelta] = {}
        mean_delta_total = 0.0
        compared_count = 0

        for receiver_id in receiver_ids:
            a = result_a.receiver_stats.get(receiver_id)
            b = result_b.receiver_stats.get(receiver_id)
            if a is None:
                a = b.__class__(0.0, 0.0, 0.0, 0)  # type: ignore[union-attr]
            if b is None:
                b = a.__class__(0.0, 0.0, 0.0, 0)
            delta = ReceiverDelta(
                min_db_delta=b.min_db - a.min_db,
                max_db_delta=b.max_db - a.max_db,
                mean_db_delta=b.mean_db - a.mean_db,
                sample_count_delta=b.sample_count - a.sample_count,
            )
            receiver_deltas[receiver_id] = delta
            mean_delta_total += delta.mean_db_delta
            compared_count += 1

        return RunResultComparison(
            project=result_a.run.project,
            scenario_a=result_a.run.scenario,
            scenario_b=result_b.run.scenario,
            run_a_id=result_a.run.run_id,
            run_b_id=result_b.run.run_id,
            receiver_deltas=receiver_deltas,
            summary={
                'receiver_count_compared': compared_count,
                'mean_of_mean_db_deltas': (mean_delta_total / compared_count) if compared_count else 0.0,
                'largest_mean_db_increase_receiver': self._largest_delta_receiver(receiver_deltas, reverse=True),
                'largest_mean_db_decrease_receiver': self._largest_delta_receiver(receiver_deltas, reverse=False),
            },
        )

    def _largest_delta_receiver(self, receiver_deltas: dict[str, ReceiverDelta], reverse: bool) -> dict[str, object] | None:
        if not receiver_deltas:
            return None
        receiver_id, delta = sorted(
            receiver_deltas.items(),
            key=lambda item: item[1].mean_db_delta,
            reverse=reverse,
        )[0]
        return {
            'receiver_id': receiver_id,
            'mean_db_delta': delta.mean_db_delta,
        }

    def _flatten_scenario(self, scenario: ScenarioConfig) -> dict[str, object]:
        noise_barrier_definitions = tuple(
            (
                barrier.id,
                barrier.x1,
                barrier.y1,
                barrier.x2,
                barrier.y2,
                barrier.height_meters,
                barrier.attenuation_db,
                barrier.material,
                barrier.propagation.reflection_loss_db,
                barrier.propagation.diffraction_loss_db,
                barrier.propagation.absorption_coefficient,
                barrier.propagation.allows_reflection,
                barrier.propagation.allows_diffraction,
            )
            for barrier in scenario.scene.noise_barriers
        )
        building_definitions = tuple(
            (
                building.id,
                tuple(building.footprint),
                building.height_meters,
                building.attenuation_db,
                building.material,
                building.propagation.reflection_loss_db,
                building.propagation.diffraction_loss_db,
                building.propagation.absorption_coefficient,
                building.propagation.allows_reflection,
                building.propagation.allows_diffraction,
            )
            for building in scenario.scene.buildings
        )
        return {
            'traffic.max_vehicles': scenario.traffic.max_vehicles,
            'traffic.vehicle_types': tuple(scenario.traffic.vehicle_types),
            'traffic.vehicle_weights': tuple(scenario.traffic.vehicle_weights),
            'traffic.start_mode': scenario.traffic.start_mode,
            'traffic.vehicle_interval_seconds': scenario.traffic.vehicle_interval_seconds,
            'traffic.start_speed_kmh': scenario.traffic.start_speed_kmh,
            'traffic.route_types': tuple(scenario.traffic.route_types),
            'controls.lane_change_mode': scenario.controls.lane_change_mode,
            'controls.lane_change_ratio': scenario.controls.lane_change_ratio,
            'controls.lane_change_strategy': scenario.controls.lane_change_strategy,
            'controls.lane_change_force_change': scenario.controls.lane_change_force_change,
            'controls.lane_change_check_radius_meters': scenario.controls.lane_change_check_radius_meters,
            'controls.lane_change_restore_time_seconds': scenario.controls.lane_change_restore_time_seconds,
            'controls.target_lane_index': scenario.controls.target_lane_index,
            'controls.designated_lane': scenario.controls.designated_lane,
            'controls.lane_change_target_positions': tuple(scenario.controls.lane_change_target_positions),
            'controls.lane_change_constant_speed_kmh': scenario.controls.lane_change_constant_speed_kmh,
            'controls.lane_change_speed_change_mps': scenario.controls.lane_change_speed_change_mps,
            'controls.post_distance_speed_control': scenario.controls.post_distance_speed_control,
            'controls.post_distance_meters': scenario.controls.post_distance_meters,
            'controls.post_target_speed_kmh': scenario.controls.post_target_speed_kmh,
            'noise.background_noise_db': scenario.noise.background_noise_db,
            'noise.max_area_meters': scenario.noise.max_area_meters,
            'noise.grid_size_meters': scenario.noise.grid_size_meters,
            'noise.receiver_height_meters': scenario.noise.receiver_height_meters,
            'grid.margin_x_start': scenario.grid.margin_x_start,
            'grid.margin_x_end': scenario.grid.margin_x_end,
            'grid.extra_y_extent': scenario.grid.extra_y_extent,
            'propagation_model.reflection': tuple(asdict(scenario.propagation_model.reflection).items()),
            'propagation_model.diffraction': tuple(asdict(scenario.propagation_model.diffraction).items()),
            'scene.noise_barriers.count': len(scenario.scene.noise_barriers),
            'scene.noise_barriers.ids': tuple(barrier.id for barrier in scenario.scene.noise_barriers),
            'scene.noise_barriers.definitions': noise_barrier_definitions,
            'scene.buildings.count': len(scenario.scene.buildings),
            'scene.buildings.ids': tuple(building.id for building in scenario.scene.buildings),
            'scene.buildings.definitions': building_definitions,
            'receivers.count': len(scenario.receivers),
            'receivers.ids': tuple(receiver.id for receiver in scenario.receivers),
        }
