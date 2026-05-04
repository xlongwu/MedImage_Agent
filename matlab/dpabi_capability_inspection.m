function dpabi_capability_inspection(dpabi_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_capability_inspection';
    result.backend = 'matlab-dpabi';
    result.matlab_version = version;
    result.dpabi_dir = dpabi_dir;
    result.functions = {};
    result.summary = struct();
    result.errors = {};
    result.warnings = {};

    try
        if ~exist(dpabi_dir, 'dir')
            result.ok = false;
            result.errors{end+1} = ['DPABI directory not found: ', dpabi_dir];
        else
            addpath(genpath(dpabi_dir));
        end

        candidates = {
            'DPABI', 'dpabi_entrypoint';
            'DPARSF', 'gui_entrypoints';
            'DPARSFA', 'gui_entrypoints';
            'DPARSF_run', 'preprocessing_wrappers';
            'DPARSFA_run', 'preprocessing_wrappers';
            'y_Read', 'nifti_io';
            'y_Write', 'nifti_io';
            'y_Reslice', 'y_tools';
            'y_Smooth', 'y_tools';
            'y_RegressOutImgCovariates', 'y_tools';
            'y_bandpass', 'y_tools';
            'y_ALFF', 'y_tools';
            'y_fALFF', 'y_tools';
            'y_ReHo', 'y_tools';
            'y_CalcALFF', 'y_tools';
            'y_CalcReHo', 'y_tools';
            'rest_readfile', 'rest_tools';
            'rest_writefile', 'rest_tools';
            'rest_Smooth', 'rest_tools';
            'rest_RegressOutCovariates', 'rest_tools'
        };

        found_count = 0;
        missing_count = 0;

        for i = 1:size(candidates, 1)
            fn = candidates{i, 1};
            category = candidates{i, 2};

            item = struct();
            item.name = fn;
            item.category = category;

            try
                fn_path = which(fn);
                item.which_path = fn_path;
                item.exists = ~isempty(fn_path);

                if item.exists
                    found_count = found_count + 1;
                else
                    missing_count = missing_count + 1;
                end
            catch ME
                item.which_path = '';
                item.exists = false;
                item.error = ME.message;
                missing_count = missing_count + 1;
            end

            result.functions{end+1} = item;
        end

        result.summary.found_count = found_count;
        result.summary.missing_count = missing_count;
        result.summary.total_checked = size(candidates, 1);

        dpabi_entry = which('DPABI');
        result.summary.dpabi_entrypoint_found = ~isempty(dpabi_entry);
        result.summary.dpabi_entrypoint_path = dpabi_entry;

        if isempty(dpabi_entry)
            result.warnings{end+1} = 'DPABI entrypoint was not found. DPABI may use a different entry function or path setup may be incomplete.';
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
