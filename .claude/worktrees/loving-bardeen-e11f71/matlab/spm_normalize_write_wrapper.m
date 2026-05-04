function spm_normalize_write_wrapper(spm_dir, deformation_field, input_nii, normalize_mean, mean_nii, voxel_size_json, bounding_box_json, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_normalize_write_wrapper';
    result.backend = 'matlab-spm';
    result.deformation_field = deformation_field;
    result.input_nii = input_nii;
    result.mean_nii = mean_nii;
    result.normalized_file = '';
    result.normalized_mean_file = '';
    result.output_dir = fileparts(input_nii);
    result.voxel_size = [];
    result.bounding_box = [];
    result.errors = {};
    result.warnings = {};
    result.matlab_version = version;

    try
        if ~exist(spm_dir, 'dir')
            error(['SPM directory not found: ', spm_dir]);
        end

        if ~exist(deformation_field, 'file')
            error(['Deformation field not found: ', deformation_field]);
        end

        if ~exist(input_nii, 'file')
            error(['Input functional NIfTI not found: ', input_nii]);
        end

        addpath(spm_dir);
        spm('Defaults', 'fMRI');
        spm_jobman('initcfg');

        voxel_size = jsondecode(voxel_size_json);
        voxel_size = double(voxel_size(:)');
        result.voxel_size = voxel_size;

        bounding_box = jsondecode(bounding_box_json);
        bounding_box = double(bounding_box);
        result.bounding_box = bounding_box;

        vols = spm_vol(input_nii);
        n_frames = numel(vols);

        resample = cell(n_frames, 1);
        for i = 1:n_frames
            resample{i} = [input_nii, ',', num2str(i)];
        end

        if strcmpi(normalize_mean, 'true') && exist(mean_nii, 'file')
            resample{end+1} = [mean_nii, ',1'];
        elseif strcmpi(normalize_mean, 'true')
            result.warnings{end+1} = ['normalize_mean=true but mean_nii not found: ', mean_nii];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.normalise.write.subj.def = {deformation_field};
        matlabbatch{1}.spm.spatial.normalise.write.subj.resample = resample;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.bb = bounding_box;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.vox = voxel_size;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.interp = 4;
        matlabbatch{1}.spm.spatial.normalise.write.woptions.prefix = 'w';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);
        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        normalized_file = fullfile(input_dir, ['w', input_name, '.nii']);
        if exist(normalized_file, 'file')
            result.normalized_file = normalized_file;
        else
            error(['Expected normalized functional file not found: ', normalized_file]);
        end

        if strcmpi(normalize_mean, 'true') && exist(mean_nii, 'file')
            [mean_dir, mean_name, mean_ext] = fileparts(mean_nii);
            if strcmp(mean_ext, '.gz')
                [~, mean_name, ~] = fileparts(mean_name);
            end

            normalized_mean_file = fullfile(mean_dir, ['w', mean_name, '.nii']);
            if exist(normalized_mean_file, 'file')
                result.normalized_mean_file = normalized_mean_file;
            else
                result.warnings{end+1} = ['Expected normalized mean file not found: ', normalized_mean_file];
            end
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
