function spm_smooth_wrapper(spm_dir, input_nii, fwhm_json, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_smooth_wrapper';
    result.backend = 'matlab-spm';
    result.input_nii = input_nii;
    result.smoothed_file = '';
    result.fwhm = [];
    result.frames_total = 0;
    result.output_dir = fileparts(input_nii);
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_nii, 'file')
            error(['Input normalized functional NIfTI not found: ', input_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        fwhm = jsondecode(fwhm_json);
        fwhm = double(fwhm(:)');
        result.fwhm = fwhm;

        if numel(fwhm) ~= 3
            error('FWHM must contain exactly 3 values.');
        end

        vols = spm_vol(input_nii);
        n_frames = numel(vols);
        result.frames_total = n_frames;

        scans = cell(n_frames, 1);
        for i = 1:n_frames
            scans{i} = [input_nii, ',', num2str(i)];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.smooth.data = scans;
        matlabbatch{1}.spm.spatial.smooth.fwhm = fwhm;
        matlabbatch{1}.spm.spatial.smooth.dtype = 0;
        matlabbatch{1}.spm.spatial.smooth.im = 0;
        matlabbatch{1}.spm.spatial.smooth.prefix = 's';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);
        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        smoothed_file = fullfile(input_dir, ['s', input_name, '.nii']);

        if exist(smoothed_file, 'file')
            result.smoothed_file = smoothed_file;
        else
            error(['Expected smoothed file not found: ', smoothed_file]);
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
