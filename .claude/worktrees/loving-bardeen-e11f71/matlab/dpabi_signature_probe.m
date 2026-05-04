function dpabi_signature_probe(dpabi_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_signature_probe';
    result.backend = 'matlab-dpabi';
    result.dpabi_dir = dpabi_dir;
    result.matlab_version = version;
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
            'DPABI', 'gui_entrypoints';
            'DPARSF', 'gui_entrypoints';
            'DPARSFA', 'gui_entrypoints';
            'DPARSF_run', 'full_pipeline_runner';
            'DPARSFA_run', 'full_pipeline_runner';
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
        signature_count = 0;

        for i = 1:size(candidates, 1)
            fn = candidates{i, 1};
            category = candidates{i, 2};

            item = struct();
            item.name = fn;
            item.category = category;
            item.exists = false;
            item.which_path = '';
            item.nargin = [];
            item.nargout = [];
            item.help_excerpt = '';
            item.probe_errors = {};

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
                item.probe_errors{end+1} = ['which failed: ', ME.message];
                missing_count = missing_count + 1;
            end

            if item.exists
                try
                    item.nargin = nargin(fn);
                    signature_count = signature_count + 1;
                catch ME
                    item.probe_errors{end+1} = ['nargin failed: ', ME.message];
                end

                try
                    item.nargout = nargout(fn);
                catch ME
                    item.probe_errors{end+1} = ['nargout failed: ', ME.message];
                end

                try
                    h = help(fn);
                    if length(h) > 2000
                        h = h(1:2000);
                    end
                    item.help_excerpt = h;
                catch ME
                    item.probe_errors{end+1} = ['help failed: ', ME.message];
                end
            end

            result.functions{end+1} = item;
        end

        result.summary.found_count = found_count;
        result.summary.missing_count = missing_count;
        result.summary.signature_count = signature_count;
        result.summary.total_checked = size(candidates, 1);

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
