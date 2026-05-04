function spm_slice_timing_wrapper(spm_dir, input_nii, nslices, tr, ta, slice_order_json, reference_slice, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_slice_timing_wrapper';
    result.backend = 'matlab-spm';
    result.input_nii = input_nii;
    result.output_dir = fileparts(input_nii);
    result.corrected_file = '';
    result.nslices = str2double(nslices);
    result.tr = str2double(tr);
    result.ta = str2double(ta);
    result.reference_slice = str2double(reference_slice);
    result.slice_order = [];
    result.frames_total = 0;
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(input_nii, 'file')
            error(['Input NIfTI not found: ', input_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        slice_order = jsondecode(slice_order_json);
        slice_order = double(slice_order(:)');
        result.slice_order = slice_order;

        if numel(slice_order) ~= result.nslices
            error('slice_order length must equal nslices.');
        end

        vols = spm_vol(input_nii);
        n_frames = numel(vols);
        result.frames_total = n_frames;

        if n_frames < 2
            error('SPM slice timing requires at least 2 frames.');
        end

        scans = cell(n_frames, 1);
        for i = 1:n_frames
            scans{i} = [input_nii, ',', num2str(i)];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.temporal.st.scans = {scans};
        matlabbatch{1}.spm.temporal.st.nslices = result.nslices;
        matlabbatch{1}.spm.temporal.st.tr = result.tr;
        matlabbatch{1}.spm.temporal.st.ta = result.ta;
        matlabbatch{1}.spm.temporal.st.so = slice_order;
        matlabbatch{1}.spm.temporal.st.refslice = result.reference_slice;
        matlabbatch{1}.spm.temporal.st.prefix = 'a';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);

        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        corrected_file = fullfile(input_dir, ['a', input_name, '.nii']);

        if exist(corrected_file, 'file')
            result.corrected_file = corrected_file;
        else
            error(['Expected slice timing output not found: ', corrected_file]);
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
