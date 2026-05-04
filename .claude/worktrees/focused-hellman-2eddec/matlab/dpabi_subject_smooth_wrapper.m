function dpabi_subject_smooth_wrapper(dpabi_dir, function_name, input_nii, output_nii, fwhm_json, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_subject_smooth_wrapper';
    result.backend = 'matlab-dpabi';
    result.function_name = function_name;
    result.input_nii = input_nii;
    result.output_nii = output_nii;
    result.outputs = {};
    result.metrics = struct();
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        allowlist = {'y_Smooth', 'rest_Smooth'};
        if ~any(strcmp(function_name, allowlist))
            error(['Function is not allowlisted: ', function_name]);
        end

        if ~exist(dpabi_dir, 'dir')
            error(['DPABI directory not found: ', dpabi_dir]);
        end

        if ~exist(input_nii, 'file')
            error(['Input NIfTI not found: ', input_nii]);
        end

        addpath(genpath(dpabi_dir));

        fn_path = which(function_name);
        result.metrics.function_found = ~isempty(fn_path);
        result.metrics.function_path = fn_path;

        if isempty(fn_path)
            error(['Function not found on MATLAB path: ', function_name]);
        end

        fwhm = jsondecode(fwhm_json);
        if numel(fwhm) ~= 3
            error('FWHM must contain exactly 3 values.');
        end
        fwhm = double(fwhm(:)');

        output_dir = fileparts(output_nii);
        if ~exist(output_dir, 'dir')
            mkdir(output_dir);
        end

        result.metrics.wrapper_call_attempted = true;
        result.metrics.wrapper_call_success = false;
        result.metrics.fwhm = fwhm;

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
                    error(['y_Smooth subject wrapper failed. Manual signature review required. Last error: ', ME2.message]);
                end
            end

        elseif strcmp(function_name, 'rest_Smooth')
            try
                rest_Smooth(input_nii, output_nii, fwhm);
                result.metrics.wrapper_call_success = exist(output_nii, 'file') == 2;
                result.metrics.call_pattern = 'rest_Smooth(input_nii, output_nii, fwhm)';
            catch ME1
                result.warnings{end+1} = ['rest_Smooth call pattern failed: ', ME1.message];
                error('rest_Smooth subject wrapper failed. Manual signature review required.');
            end
        end

        if ~exist(output_nii, 'file')
            error('DPABI subject wrapper did not produce output NIfTI.');
        end

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
