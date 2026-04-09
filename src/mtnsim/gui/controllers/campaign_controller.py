from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from mtnsim.api.project_api import ProjectAPI
from mtnsim.schemas.field_campaign import FieldCampaignManifest
from mtnsim.services.campaign_validation_service import CampaignValidationService
from mtnsim.services.field_campaign_service import FieldCampaignService


class CampaignInspectWorker(QObject):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, campaign_file: str | Path, service: FieldCampaignService | None = None) -> None:
        super().__init__()
        self.campaign_file = Path(campaign_file)
        self.service = service or FieldCampaignService()

    def run(self) -> None:
        try:
            artifacts = self.service.inspect_campaign(self.campaign_file)
            self.completed.emit({
                'summary': artifacts.summary.to_dict(),
                'summary_file': str(artifacts.summary_file),
                'report_file': str(artifacts.report_file),
                'output_dir': str(artifacts.output_dir),
            })
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))


class CampaignValidateWorker(QObject):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        manifest_path: str | Path,
        campaign_file: str | Path,
        scenario_override_path: str | Path | None = None,
        use_gpu: bool = True,
        project_api: ProjectAPI | None = None,
        field_campaign_service: FieldCampaignService | None = None,
        validation_service: CampaignValidationService | None = None,
    ) -> None:
        super().__init__()
        self.manifest_path = Path(manifest_path)
        self.campaign_file = Path(campaign_file)
        self.scenario_override_path = Path(scenario_override_path) if scenario_override_path else None
        self.use_gpu = use_gpu
        self.project_api = project_api or ProjectAPI()
        self.field_campaign_service = field_campaign_service or FieldCampaignService()
        self.validation_service = validation_service or CampaignValidationService(self.field_campaign_service)

    def run(self) -> None:
        try:
            project = self.project_api.load_manifest(self.manifest_path)
            scenario_path = self.scenario_override_path
            if scenario_path is None:
                campaign = FieldCampaignManifest.load(self.campaign_file)
                if campaign.scenario_file:
                    candidate = Path(campaign.scenario_file)
                    scenario_path = candidate if candidate.is_absolute() else self.campaign_file.parent / candidate
            summary, summary_file = self.validation_service.validate_campaign(
                project,
                scenario_path,
                self.campaign_file,
                use_gpu=self.use_gpu,
            )
            self.completed.emit({
                'summary': summary.to_dict(),
                'summary_file': str(summary_file),
                'report_file': summary.campaign_validation_report_file,
                'result_summary_file': summary.result_summary_file,
                'calibration_summary_file': summary.calibration_summary_file,
                'acceptance_status': summary.acceptance_status,
            })
        except Exception as exc:  # pragma: no cover
            self.failed.emit(str(exc))


class CampaignController:
    def __init__(
        self,
        project_api: ProjectAPI | None = None,
        field_campaign_service: FieldCampaignService | None = None,
        validation_service: CampaignValidationService | None = None,
    ) -> None:
        self.project_api = project_api or ProjectAPI()
        self.field_campaign_service = field_campaign_service or FieldCampaignService()
        self.validation_service = validation_service or CampaignValidationService(self.field_campaign_service)

    def load_campaign_manifest(self, campaign_file: str | Path) -> FieldCampaignManifest:
        return FieldCampaignManifest.load(campaign_file)

    def create_inspect_worker(self, campaign_file: str | Path) -> CampaignInspectWorker:
        return CampaignInspectWorker(campaign_file, service=self.field_campaign_service)

    def create_validate_worker(
        self,
        manifest_path: str | Path,
        campaign_file: str | Path,
        scenario_override_path: str | Path | None = None,
        use_gpu: bool = True,
    ) -> CampaignValidateWorker:
        return CampaignValidateWorker(
            manifest_path=manifest_path,
            campaign_file=campaign_file,
            scenario_override_path=scenario_override_path,
            use_gpu=use_gpu,
            project_api=self.project_api,
            field_campaign_service=self.field_campaign_service,
            validation_service=self.validation_service,
        )
