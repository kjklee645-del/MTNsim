from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mtnsim.security.exceptions import ConfigValidationError, PathSecurityError

if TYPE_CHECKING:
    from mtnsim.schemas.field_campaign import FieldCampaignManifest
    from mtnsim.schemas.project import ProjectManifest


def project_root_from_manifest_path(manifest_path: str | Path) -> Path:
    path = Path(manifest_path).expanduser().resolve()
    parent = path.parent
    if parent.name == "examples":
        return parent.parent
    return parent


def project_root_from_manifest(project: "ProjectManifest") -> Path:
    if project.source_path is None:
        raise ConfigValidationError("Project manifest source_path is required to resolve project-scoped paths.")
    return project_root_from_manifest_path(project.source_path)


def campaign_root_from_manifest_path(campaign_path: str | Path) -> Path:
    return Path(campaign_path).expanduser().resolve().parent


def campaign_root_from_manifest(campaign: "FieldCampaignManifest") -> Path:
    if campaign.source_path is None:
        raise ConfigValidationError("Field campaign source_path is required to resolve campaign-scoped paths.")
    return campaign_root_from_manifest_path(campaign.source_path)


def validate_path_within_root(
    root: str | Path,
    raw_path: str | Path,
    *,
    label: str,
    allow_empty: bool = False,
) -> Path | None:
    root_path = Path(root).expanduser().resolve()
    raw_text = str(raw_path).strip()
    if not raw_text:
        if allow_empty:
            return None
        raise ConfigValidationError(f"{label} must not be empty.")

    candidate = Path(raw_text).expanduser()
    resolved = candidate.resolve() if candidate.is_absolute() else (root_path / candidate).resolve()
    _ensure_relative_to(resolved, root_path, label=label)
    return resolved


def resolve_path_within_root(
    root: str | Path,
    raw_path: str | Path,
    *,
    label: str,
    allow_empty: bool = False,
    must_exist: bool = True,
    expected_kind: str | None = None,
) -> Path | None:
    resolved = validate_path_within_root(root, raw_path, label=label, allow_empty=allow_empty)
    if resolved is None:
        return None
    if must_exist and not resolved.exists():
        raise ConfigValidationError(f"{label} does not exist: {resolved}")
    if expected_kind == "file" and resolved.exists() and not resolved.is_file():
        raise ConfigValidationError(f"{label} must point to a file: {resolved}")
    if expected_kind == "dir" and resolved.exists() and not resolved.is_dir():
        raise ConfigValidationError(f"{label} must point to a directory: {resolved}")
    return resolved


def resolve_project_path(
    project: "ProjectManifest",
    raw_path: str | Path,
    *,
    label: str,
    allow_empty: bool = False,
    must_exist: bool = True,
    expected_kind: str | None = None,
) -> Path | None:
    return resolve_path_within_root(
        project_root_from_manifest(project),
        raw_path,
        label=label,
        allow_empty=allow_empty,
        must_exist=must_exist,
        expected_kind=expected_kind,
    )


def resolve_project_output_root(project: "ProjectManifest", *, must_exist: bool = False) -> Path:
    resolved = resolve_project_path(
        project,
        project.paths.outputs,
        label="project.paths.outputs",
        allow_empty=False,
        must_exist=must_exist,
    )
    assert resolved is not None
    return resolved


def resolve_campaign_path(
    campaign: "FieldCampaignManifest",
    raw_path: str | Path,
    *,
    label: str,
    allow_empty: bool = False,
    must_exist: bool = True,
    expected_kind: str | None = None,
) -> Path | None:
    return resolve_path_within_root(
        campaign_root_from_manifest(campaign),
        raw_path,
        label=label,
        allow_empty=allow_empty,
        must_exist=must_exist,
        expected_kind=expected_kind,
    )


def _ensure_relative_to(path: Path, root: Path, *, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise PathSecurityError(f"{label} escapes its allowed root. root={root} path={path}") from exc
