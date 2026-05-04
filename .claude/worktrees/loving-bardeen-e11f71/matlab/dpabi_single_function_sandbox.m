function dpabi_single_function_sandbox(dpabi_dir, function_name, sandbox_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_single_function_sandbox';
    result.backend = 'matlab-dpabi';
    result.function_name = function_name;
    result.dpabi_dir = dpabi_dir;
    result.sandbox_dir = sandbox_dir;
    result.matlab_version = version;
    result.outputs = {};
    result.metrics = struct();
    result.errors = {};
    result.warnings = {};

    try
        allowlist = {'y_Smooth', 'rest_Smooth'};
        if ~any(strcmp(function_name, allowlist))
            error(['Function is not allowlisted for sandbox execution: ', function_name]);
        end

        if ~exist(dpabi_dir, 'dir')
            error(['DPABI directory not found: ', dpabi_dir]);
        end

        if ~exist(sandbox_dir, 'dir')
            mkdir(sandbox_dir);
        end

        addpath(genpath(dpabi_dir));

        input_nii = fullfile(sandbox_dir, 'input_synthetic.nii');
        output_nii = fullfile(sandbox_dir, 'smoothed_synthetic.nii');

        fn_path = which(function_name);
        result.metrics.function_found = ~isempty(fn_path);
        result.metrics.function_path = fn_path;

        if isempty(fn_path)
            error(['Function not found on MATLAB path: ', function_name]);
        end

        data = single(randn(16, 16, 16));

        if isempty(which('spm_write_vol'))
            error('spm_write_vol not found. Cannot create synthetic NIfTI.');
        end

        V = struct();
        V.fname = input_nii;
        V.dim = size(data);
        V.dt = [16 0];
        V.mat = eye(4);
        V.pinfo = [1; 0; 0];
        V.descrip = 'Synthetic NIfTI for DPABI single-function wrapper test';

        spm_write_vol(V, data);

        if ~exist(input_nii, 'file')
            error('Failed to create synthetic input NIfTI.');
        end

        result.metrics.input_exists = exist(input_nii, 'file') == 2;
        result.metrics.wrapper_call_attempted = true;
        result.metrics.wrapper_call_success = false;

        fwhm = [4 4 4];

        if strcmp(function_name, 'y_Smooth')
            try
                y_Smooth(input_nii, output_nii, fwhm);
                result.metrics.wrapper_call_success = exist(output_nii, 'file') == 2;
                result.metrics.call_pattern = 'y_Smooth(input_nii, output_nii, fwhm)';
            catch ME1
                result.warnings{end+1} = ['First y_Smooth call pattern failed: ', ME1.message];

                try
                    y_Smooth({input_nii}, {output_nii}, fwhm);
                    result.metrics.wrapper_call_success = exist(output_nii, 'file') == 2;
                    result.metrics.call_pattern = 'y_Smooth({input_nii}, {output_nii}, fwhm)';
                catch ME2
                    error(['y_Smooth sandbox wrapper failed. Manual signature review required. Last error: ', ME2.message]);
                end
            end

        elseif strcmp(function_name, 'rest_Smooth')
            try
                rest_Smooth(input_nii, output_nii, fwhm);
                result.metrics.wrapper_call_success = exist(output_nii, 'file') == 2;
                result.metrics.call_pattern = 'rest_Smooth(input_nii, output_nii, fwhm)';
            catch ME1
                result.warnings{end+1} = ['rest_Smooth call pattern failed: ', ME1.message];
                error('rest_Smooth sandbox wrapper failed. Manual signature review required.');
            end
        end

        if ~exist(output_nii, 'file')
            error('Single-function wrapper did not produce smoothed_synthetic.nii.');
        end

        result.outputs{end+1} = input_nii;
        result.outputs{end+1} = output_nii;
        result.metrics.output_exists = exist(output_nii, 'file') == 2;

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
