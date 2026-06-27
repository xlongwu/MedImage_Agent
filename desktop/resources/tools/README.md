# Bundled dcm2niix Resources

This directory holds the bundled `dcm2niix.exe` binary and its metadata,
shipped with the MedImage Agent desktop application so users do not need
to install dcm2niix separately.

## Required files

```
windows-x64/
├── dcm2niix.exe       # The actual binary (added at build/release time)
├── LICENSE.txt         # BSD 3-Clause license
└── dcm2niix.sha256     # SHA256 of dcm2niix.exe for integrity verification
```

## Adding the binary

The `dcm2niix.exe` binary is NOT committed to this repository. It must be
added during the release/build process from a fixed, verified release asset:

1. Download a pinned dcm2niix release for Windows x64 from
   https://github.com/rordenlab/dcm2niix/releases
2. Verify the SHA256 matches the value recorded in `dcm2niix.sha256`.
3. Place `dcm2niix.exe` in this directory before running
   `desktop/packaging/build_backend.ps1`.

The PyInstaller spec at `desktop/packaging/pyinstaller_backend.spec`
automatically bundles every file in this directory into the backend
executable under `resources/tools/windows-x64/`.

## Runtime detection

The backend resolves the bundled binary in this order
(per `实现dcm2nii任务方案.md` §9.3):

1. Desktop config `dicom_conversion.dcm2niix_path`
2. `MEDIMAGE_DCM2NIIX_PATH` env var
3. Active mamba/conda env
4. System PATH
5. Bundled resource (this directory or PyInstaller `resources/tools/`)
6. Legacy dev `tools/dcm2niix.exe`
7. Not found

## Version pinning

The expected version is pinned in
`src/backend/app/services/dicom_conversion_execution.py` as
`_DCM2NIIX_EXPECTED_VERSION`. Update both the binary and the expected
version together.
