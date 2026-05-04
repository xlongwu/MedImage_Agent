function spm_smoke_test(spm_dir, output_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_smoke_test';
    result.backend = 'matlab-spm';
    result.outputs = {};
    result.errors = {};
    result.metrics = struct();

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(output_dir, 'dir')
            mkdir(output_dir);
        end

        addpath(spm_dir);

        try
            spm('defaults', 'fmri');
            spm_jobman('initcfg');
        catch ME
            result.errors{end+1} = ['SPM init warning: ', ME.message];
        end

        input_nii = fullfile(output_dir, 'input.nii');
        smoothed_nii = fullfile(output_dir, 'smoothed.nii');

        data = single(randn(20, 20, 20));

        V = struct();
        V.fname = input_nii;
        V.dim = size(data);
        V.dt = [16 0];
        V.mat = eye(4);
        V.pinfo = [1; 0; 0];
        V.descrip = 'Synthetic NIfTI for SPM smoke test';

        spm_write_vol(V, data);

        if ~exist(input_nii, 'file')
            error('Failed to create synthetic input NIfTI.');
        end

        spm_smooth(input_nii, smoothed_nii, [4 4 4]);

        if ~exist(smoothed_nii, 'file')
            error('SPM smoothing did not produce output NIfTI.');
        end

        result.outputs{end+1} = input_nii;
        result.outputs{end+1} = smoothed_nii;
        result.metrics.input_exists = exist(input_nii, 'file') == 2;
        result.metrics.smoothed_exists = exist(smoothed_nii, 'file') == 2;
        result.metrics.image_shape = [20 20 20];
        result.metrics.smooth_fwhm = [4 4 4];

    catch ME
        result.ok = false;
        try
            result.errors{end+1} = getReport(ME, 'extended', 'hyperlinks', 'off');
        catch
            result.errors{end+1} = [ME.identifier, ': ', ME.message];
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
