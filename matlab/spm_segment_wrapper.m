function spm_segment_wrapper(spm_dir, input_t1w, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_segment_wrapper';
    result.backend = 'matlab-spm';
    result.input_t1w = input_t1w;
    result.output_dir = fileparts(input_t1w);
    result.gm_file = '';
    result.wm_file = '';
    result.csf_file = '';
    result.deformation_field = '';
    result.native_tissue_files = {};
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_t1w, 'file')
            error(['Input T1w not found: ', input_t1w]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        tpm_path = fullfile(spm_dir, 'tpm', 'TPM.nii');
        if ~exist(tpm_path, 'file')
            error(['SPM TPM not found: ', tpm_path]);
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.preproc.channel.vols = {[input_t1w, ',1']};
        matlabbatch{1}.spm.spatial.preproc.channel.biasreg = 0.001;
        matlabbatch{1}.spm.spatial.preproc.channel.biasfwhm = 60;
        matlabbatch{1}.spm.spatial.preproc.channel.write = [0 0];

        for tissue_index = 1:6
            matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).tpm = ...
                {[tpm_path, ',', num2str(tissue_index)]};

            if tissue_index <= 3
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).ngaus = tissue_index;
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).native = [1 0];
            else
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).ngaus = 2;
                matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).native = [0 0];
            end

            matlabbatch{1}.spm.spatial.preproc.tissue(tissue_index).warped = [0 0];
        end

        matlabbatch{1}.spm.spatial.preproc.warp.mrf = 1;
        matlabbatch{1}.spm.spatial.preproc.warp.cleanup = 1;
        matlabbatch{1}.spm.spatial.preproc.warp.reg = [0 0.001 0.5 0.05 0.2];
        matlabbatch{1}.spm.spatial.preproc.warp.affreg = 'mni';
        matlabbatch{1}.spm.spatial.preproc.warp.fwhm = 0;
        matlabbatch{1}.spm.spatial.preproc.warp.samp = 3;
        matlabbatch{1}.spm.spatial.preproc.warp.write = [0 1];

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_t1w);
        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        gm_file = fullfile(input_dir, ['c1', input_name, '.nii']);
        wm_file = fullfile(input_dir, ['c2', input_name, '.nii']);
        csf_file = fullfile(input_dir, ['c3', input_name, '.nii']);
        deformation_field = fullfile(input_dir, ['y_', input_name, '.nii']);

        if exist(gm_file, 'file')
            result.gm_file = gm_file;
            result.native_tissue_files{end+1} = gm_file;
        else
            result.warnings{end+1} = ['Expected GM file not found: ', gm_file];
        end

        if exist(wm_file, 'file')
            result.wm_file = wm_file;
            result.native_tissue_files{end+1} = wm_file;
        else
            result.warnings{end+1} = ['Expected WM file not found: ', wm_file];
        end

        if exist(csf_file, 'file')
            result.csf_file = csf_file;
            result.native_tissue_files{end+1} = csf_file;
        else
            result.warnings{end+1} = ['Expected CSF file not found: ', csf_file];
        end

        if exist(deformation_field, 'file')
            result.deformation_field = deformation_field;
        else
            result.warnings{end+1} = ['Expected deformation field not found: ', deformation_field];
        end

        if isempty(result.gm_file) || isempty(result.wm_file) || isempty(result.csf_file)
            error('SPM segmentation did not produce required tissue maps.');
        end

        if isempty(result.deformation_field)
            error('SPM segmentation did not produce deformation field.');
        end

    catch ME
        result.ok = false;
        try
            result.errors{end+1} = getReport(ME, 'extended', 'hyperlinks', 'off');
        catch
            result.errors{end+1} = ME.message;
        end
    end

    fid = fopen(output_json, 'w');
    if fid == -1
        error(['Cannot open output JSON for writing: ', output_json]);
    end

    fwrite(fid, jsonencode(result), 'char');
    fclose(fid);

    if ~result.ok
        exit(1);
    end
end
