"""Service adapter for artifact and image routes.

Thin adapter that accepts ProjectStore and delegates to the existing
artifact/image service functions.  Preserves all current behavior; only
changes how the store is supplied (Depends injection instead of module-level
mock_store).
"""

from __future__ import annotations

from src.backend.app.api.dependencies import ProjectStore


def build_image_preview(
    project_id: str,
    subject_id: str | None,
    sequence: str,
    slice_index: int | None,
    plane: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.image_preview import build_image_preview as _build

    search_roots = store.list_import_paths(project_id)
    return _build(
        project_id=project_id,
        subject_id=subject_id,
        sequence=sequence,
        slice_index=slice_index,
        plane=plane,
        search_roots=search_roots,
    ).model_dump()


def list_image_sources(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.image_preview import list_image_sources as _list

    return _list(
        project_id=project_id,
        search_roots=store.list_import_paths(project_id),
    ).model_dump()


def build_image_validation_report(
    project_id: str,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.image_preview import build_image_validation_report as _build

    project = store.get_project(project_id)
    expected_sequences = project.sequences if project else []
    return _build(
        project_id=project_id,
        expected_sequences=expected_sequences,
        search_roots=store.list_import_paths(project_id),
    ).model_dump()


def build_nifti_thumbnail(
    project_id: str,
    image_id: str,
    view: str,
    volume_index: int | None,
    size: int | None,
    store: ProjectStore,
) -> dict[str, object]:
    from src.backend.app.services.nifti_thumbnail import build_nifti_thumbnail as _build

    return _build(project_id, image_id, view, volume_index, size).model_dump()
