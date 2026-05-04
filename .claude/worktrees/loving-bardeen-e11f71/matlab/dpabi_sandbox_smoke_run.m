function dpabi_sandbox_smoke_run(dpabi_dir, sandbox_dir, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'dpabi_sandbox_smoke_run';
    result.backend = 'matlab-dpabi';
    result.dpabi_dir = dpabi_dir;
    result.sandbox_dir = sandbox_dir;
    result.matlab_version = version;
    result.outputs = {};
    result.metrics = struct();
    result.errors = {};
    result.warnings = {};

    try
        if ~exist(dpabi_dir, 'dir')
            error(['DPABI directory not found: ', dpabi_dir]);
        end

        if ~exist(sandbox_dir, 'dir')
            mkdir(sandbox_dir);
        end

        addpath(genpath(dpabi_dir));

        input_nii = fullfile(sandbox_dir, 'input_synthetic.nii');
        output_nii = fullfile(sandbox_dir, 'output_synthetic.nii');

        y_read_path = which('y_Read');
        y_write_path = which('y_Write');
        rest_read_path = which('rest_readfile');
        rest_write_path = which('rest_writefile');

        result.metrics.y_Read_found = ~isempty(y_read_path);
        result.metrics.y_Write_found = ~isempty(y_write_path);
        result.metrics.rest_readfile_found = ~isempty(rest_read_path);
        result.metrics.rest_writefile_found = ~isempty(rest_write_path);

        data = single(randn(8, 8, 8));

        V = struct();
        V.fname = input_nii;
        V.dim = size(data);
        V.dt = [16 0];
        V.mat = eye(4);
        V.pinfo = [1; 0; 0];
        V.descrip = 'Synthetic NIfTI for DPABI sandbox smoke test';

        spm_found = ~isempty(which('spm_write_vol'));
        result.metrics.spm_write_vol_found = spm_found;

        if spm_found
            spm_write_vol(V, data);
        else
            error('spm_write_vol not found. Cannot create synthetic NIfTI in MATLAB sandbox.');
        end

        if ~exist(input_nii, 'file')
            error('Failed to create synthetic input NIfTI.');
        end

        result.metrics.read_write_test_attempted = false;
        result.metrics.read_write_test_success = false;
        result.metrics.used_function_family = '';

        if ~isempty(y_read_path) && ~isempty(y_write_path)
            result.metrics.read_write_test_attempted = true;
            result.metrics.used_function_family = 'y_Read_y_Write';

            try
                [Data, Header] = y_Read(input_nii);
                y_Write(Data, Header, output_nii);
                result.metrics.read_write_test_success = exist(output_nii, 'file') == 2;
            catch ME
                result.warnings{end+1} = ['y_Read/y_Write smoke test failed: ', ME.message];
            end

        elseif ~isempty(rest_read_path) && ~isempty(rest_write_path)
            result.metrics.read_write_test_attempted = true;
            result.metrics.used_function_family = 'rest_readfile_rest_writefile';

            try
                [Data, Header] = rest_readfile(input_nii);
                rest_writefile(Data, output_nii, Header);
                result.metrics.read_write_test_success = exist(output_nii, 'file') == 2;
            catch ME
                result.warnings{end+1} = ['rest_readfile/rest_writefile smoke test failed: ', ME.message];
            end

        else
            result.warnings{end+1} = 'No supported DPABI/REST read-write function pair found. Smoke run only verified addpath and synthetic NIfTI creation.';
        end

        if ~exist(output_nii, 'file')
            Vout = V;
            Vout.fname = output_nii;
            spm_write_vol(Vout, data);
            result.warnings{end+1} = 'Used SPM fallback to create output_synthetic.nii.';
        end

        if ~exist(output_nii, 'file')
            error('Sandbox output NIfTI was not produced.');
        end

        result.outputs{end+1} = input_nii;
        result.outputs{end+1} = output_nii;
        result.metrics.input_exists = exist(input_nii, 'file') == 2;
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
