"""Reviewed native DICOM conversion node plugin."""

from __future__ import annotations

from src.backend.app.services.reviewed_conversion_service import ReviewedConversionService


def run_native_dicom_conversion(context, node):
    store = (
        context.tool_execution_context.ticket_service.store
        if context.tool_execution_context is not None
        else None
    )
    return ReviewedConversionService().execute_node(context=context, node=node, store=store)


REGISTRY = {ReviewedConversionService.NODE_ID: run_native_dicom_conversion}
