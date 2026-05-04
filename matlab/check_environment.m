function check_environment(spm_dir, dpabi_dir, output_json)
    result = struct();
    result.ok = true;
    result.errors = {};
    result.matlab_version = version;
    result.spm_path = '';
    result.dpabi_path = '';

    if ~exist(spm_dir, 'dir')
        result.ok = false;
        result.errors{end+1} = ['SPM directory not found: ', spm_dir];
    else
        addpath(spm_dir);
        try
            spm_path = which('spm');
            result.spm_path = spm_path;
            if isempty(spm_path)
                result.ok = false;
                result.errors{end+1} = 'SPM function not found after addpath.';
            end
        catch ME
            result.ok = false;
            result.errors{end+1} = ['SPM check failed: ', ME.message];
        end
    end

    if ~exist(dpabi_dir, 'dir')
        result.ok = false;
        result.errors{end+1} = ['DPABI directory not found: ', dpabi_dir];
    else
        addpath(genpath(dpabi_dir));
        try
            dpabi_main = which('DPABI');
            result.dpabi_path = dpabi_main;
            if isempty(dpabi_main)
                result.errors{end+1} = 'DPABI function not found after addpath. This may be acceptable if DPABI entry file has a different name.';
            end
        catch ME
            result.ok = false;
            result.errors{end+1} = ['DPABI check failed: ', ME.message];
        end
    end

    fid = fopen(output_json, 'w');
    if fid == -1
        error(['Cannot open output JSON for writing: ', output_json]);
    end
    fwrite(fid, jsonencode(result), 'char');
    fclose(fid);
end
