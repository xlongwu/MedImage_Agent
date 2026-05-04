function spm_smooth_4d(spm_dir, input_nii, output_nii, output_json, fwhm)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_smooth_subject';
    result.backend = 'matlab-spm';
    result.input = input_nii;
    result.output = output_nii;
    result.outputs = {};
    result.metrics = struct();
    result.errors = {};

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_nii, 'file')
            error(['Input NIfTI not found: ', input_nii]);
        end

        output_dir = fileparts(output_nii);
        if ~exist(output_dir, 'dir')
            mkdir(output_dir);
        end

        if exist(output_nii, 'file')
            delete(output_nii);
        end

        addpath(spm_dir);

        try
            spm('defaults', 'fmri');
            spm_jobman('initcfg');
        catch ME
            result.errors{end+1} = ['SPM init warning: ', ME.message];
        end

        V = spm_vol(input_nii);
        n_volumes = numel(V);

        for i = 1:n_volumes
            Y = spm_read_vols(V(i));
            Ys = zeros(size(Y), 'single');

            try
                spm_smooth(Y, Ys, fwhm);
            catch
                % Fallback: use temporary files if matrix-based smoothing fails
                tmp_in = fullfile(output_dir, ['tmp_vol_', num2str(i), '.nii']);
                tmp_out = fullfile(output_dir, ['tmp_smooth_', num2str(i), '.nii']);

                Vtmp = V(i);
                Vtmp.fname = tmp_in;
                Vtmp.n = [1 1];
                spm_write_vol(Vtmp, Y);

                spm_smooth(tmp_in, tmp_out, fwhm);

                Vsm = spm_vol(tmp_out);
                Ys = spm_read_vols(Vsm);

                if exist(tmp_in, 'file')
                    delete(tmp_in);
                end
                if exist(tmp_out, 'file')
                    delete(tmp_out);
                end
            end

            Vout = V(i);
            Vout.fname = output_nii;
            Vout.dt = [16 0];
            Vout.pinfo = [1; 0; 0];
            Vout.descrip = 'SPM smoothed synthetic BOLD';
            Vout.n = [i 1];

            spm_write_vol(Vout, Ys);
        end

        if ~exist(output_nii, 'file')
            error('SPM smoothing did not produce output NIfTI.');
        end

        result.outputs{end+1} = output_nii;
        result.metrics.n_volumes = n_volumes;
        result.metrics.fwhm = fwhm;
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
