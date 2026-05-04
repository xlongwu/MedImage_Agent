function spm_coregister_wrapper(spm_dir, reference_nii, source_nii, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_coregister_wrapper';
    result.backend = 'matlab-spm';
    result.reference_nii = reference_nii;
    result.source_nii = source_nii;
    result.coregistered_file = '';
    result.output_dir = fileparts(source_nii);
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(reference_nii, 'file')
            error(['Reference NIfTI not found: ', reference_nii]);
        end

        if ~exist(source_nii, 'file')
            error(['Source NIfTI not found: ', source_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        [source_dir, source_name, source_ext] = fileparts(source_nii);
        if strcmp(source_ext, '.gz')
            [~, source_name, ~] = fileparts(source_name);
        end

        coregistered_file = fullfile(source_dir, ['coreg_', source_name, '.nii']);
        copyfile(source_nii, coregistered_file);

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.coreg.estimate.ref = {[reference_nii, ',1']};
        matlabbatch{1}.spm.spatial.coreg.estimate.source = {[coregistered_file, ',1']};
        matlabbatch{1}.spm.spatial.coreg.estimate.other = {''};
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.cost_fun = 'nmi';
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.sep = [4 2];
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.tol = ...
            [0.02 0.02 0.02 0.001 0.001 0.001 0.01 0.01 0.01 0.001 0.001 0.001];
        matlabbatch{1}.spm.spatial.coreg.estimate.eoptions.fwhm = [7 7];

        spm_jobman('run', matlabbatch);

        if exist(coregistered_file, 'file')
            result.coregistered_file = coregistered_file;
        else
            error(['Expected coregistered file not found: ', coregistered_file]);
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
