from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from mtnsim.api.project_api import ProjectAPI
from mtnsim.api.simulation_api import SimulationAPI


class RunWorker(QObject):
    progress_changed = Signal(int, str)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        manifest_path: str | Path,
        scenario_path: str | Path,
        use_gpu: bool = True,
        record_vehicle_trace: bool = False,
        project_api: ProjectAPI | None = None,
        simulation_api: SimulationAPI | None = None,
    ) -> None:
        super().__init__()
        self.manifest_path = Path(manifest_path)
        self.scenario_path = Path(scenario_path)
        self.use_gpu = use_gpu
        self.record_vehicle_trace = record_vehicle_trace
        self.project_api = project_api or ProjectAPI()
        self.simulation_api = simulation_api or SimulationAPI()

    def run(self) -> None:
        try:
            project = self.project_api.load_manifest(self.manifest_path)
            scenario = self.project_api.load_scenario(self.scenario_path)
            self.progress_changed.emit(2, 'Loading project and scenario')

            artifacts = self.simulation_api.run(
                project,
                scenario,
                use_gpu=self.use_gpu,
                progress_callback=self._emit_progress,
                record_vehicle_trace=self.record_vehicle_trace,
            )
            self.completed.emit(
                {
                    'run_id': artifacts.run_id,
                    'output_dir': str(artifacts.output_dir),
                    'manifest_file': str(artifacts.manifest_file),
                    'result_summary_file': str(artifacts.result_summary_file),
                    'final_grid_snapshot_file': str(artifacts.final_grid_snapshot_file) if artifacts.final_grid_snapshot_file else None,
                    'vehicle_trace_file': str(artifacts.vehicle_trace_file) if artifacts.vehicle_trace_file else None,
                    'receiver_history_files': {key: str(value) for key, value in artifacts.receiver_history_files.items()},
                    'run_summary': artifacts.run_summary.to_dict(),
                }
            )
        except Exception as exc:  # pragma: no cover - threaded UI path
            self.failed.emit(str(exc))

    def _emit_progress(self, progress: dict) -> None:
        percent = int(progress.get('percent', 0))
        label = str(progress.get('message', 'Running'))
        self.progress_changed.emit(percent, label)


class RunController:
    def __init__(self, project_api: ProjectAPI | None = None, simulation_api: SimulationAPI | None = None) -> None:
        self.project_api = project_api or ProjectAPI()
        self.simulation_api = simulation_api or SimulationAPI()

    def create_worker(
        self,
        manifest_path: str | Path,
        scenario_path: str | Path,
        use_gpu: bool = True,
        record_vehicle_trace: bool = False,
    ) -> RunWorker:
        return RunWorker(
            manifest_path=manifest_path,
            scenario_path=scenario_path,
            use_gpu=use_gpu,
            record_vehicle_trace=record_vehicle_trace,
            project_api=self.project_api,
            simulation_api=self.simulation_api,
        )
