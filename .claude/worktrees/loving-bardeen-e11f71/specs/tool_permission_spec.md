# Tool Permission Spec

Every tool must declare its permission and safety attributes.

## Required Fields

- name
- read_only
- writes_files
- destructive
- requires_confirmation
- parallel_safe
- allowed_read_paths
- allowed_write_paths

## Risk Principles

Risk is determined by:

1. Reversibility: can the action be undone?
2. Blast radius: does the action affect only local workspace or shared systems?

## Example

```yaml
name: matlab.check_environment
read_only: false
writes_files: true
destructive: false
requires_confirmation: false
parallel_safe: false
allowed_read_paths:
  - third_party/
  - matlab/
  - examples/
allowed_write_paths:
  - work/
  - logs/
```

## Default Safety Rules

- rawdata/ is read-only.
- sourcedata/ is read-only.
- derivatives/ is writable only with explicit configuration.
- work/, logs/, reports/ are writable.
- Deleting files requires confirmation.
- Overwriting derivatives requires confirmation.
- Uploading medical imaging data to external services is forbidden unless explicitly approved and de-identified.
