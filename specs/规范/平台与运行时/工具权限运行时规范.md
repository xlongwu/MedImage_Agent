# Tool Permission Runtime

This document defines the tool permission system for the MedImage Agent Runtime.

## Overview

The tool permission runtime provides:

- Tool registry with metadata
- Permission checking before tool execution
- Read-only vs read-write classification
- Destructive operation detection
- Confirmation requirements
- Path allowlists

## Tool Spec

Each tool has the following metadata:

| Field | Type | Description |
|-------|------|-------------|
| name | str | Tool identifier |
| description | str | Human-readable description |
| read_only | bool | Whether tool only reads data |
| writes_files | bool | Whether tool writes files |
| destructive | bool | Whether tool can delete/overwrite |
| requires_confirmation | bool | Whether explicit approval needed |
| parallel_safe | bool | Whether tool can run in parallel |
| allowed_read_paths | list[str] | Allowed paths for reading |
| allowed_write_paths | list[str] | Allowed paths for writing |

## Registered Tools

### pipeline.plan

- **read_only**: false (writes plan.json)
- **writes_files**: true
- **destructive**: false
- **requires_confirmation**: false
- **parallel_safe**: true

### pipeline.execute

- **read_only**: false
- **writes_files**: true
- **destructive**: false
- **requires_confirmation**: true
- **parallel_safe**: false

## Permission Checks

Before executing a tool:

1. Check if tool exists in registry
2. If requires_confirmation, verify approval flag
3. Verify paths are within allowed directories
4. Log permission check results

## Safety Rules

- Tools with requires_confirmation=true cannot run without explicit approval
- Destructive tools should always require confirmation
- Read-only tools should not write files
- Path validation prevents directory traversal attacks
