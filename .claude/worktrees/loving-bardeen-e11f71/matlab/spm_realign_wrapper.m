function spm_realign_wrapper(spm_dir, input_nii, output_json)
    result = struct();
    result.ok = true;
    result.node_id = 'spm_realign_wrapper';
    result.backend = 'matlab-spm';
    result.input_nii = input_nii;
    result.output_dir = fileparts(input_nii);
    result.realigned_files = {};
    result.mean_file = '';
    result.motion_parameter_file = '';
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

        vols = spm_vol(input_nii);
        n_frames = numel(vols);
        result.frames_total = n_frames;

        if n_frames < 2
            error('SPM realignment requires at least 2 frames.');
        end

        scans = cell(n_frames, 1);
        for i = 1:n_frames
            scans{i} = [input_nii, ',', num2str(i)];
        end

        matlabbatch = {};
        matlabbatch{1}.spm.spatial.realign.estwrite.data = {scans};
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.quality = 0.9;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.sep = 4;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.fwhm = 5;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.rtm = 1;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.interp = 2;
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.wrap = [0 0 0];
        matlabbatch{1}.spm.spatial.realign.estwrite.eoptions.weight = '';
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.which = [2 1];
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.interp = 4;
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.wrap = [0 0 0];
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.mask = 1;
        matlabbatch{1}.spm.spatial.realign.estwrite.roptions.prefix = 'r';

        spm_jobman('run', matlabbatch);

        [input_dir, input_name, input_ext] = fileparts(input_nii);

        if strcmp(input_ext, '.gz')
            [~, input_name, ~] = fileparts(input_name);
        end

        realigned_file = fullfile(input_dir, ['r', input_name, '.nii']);
        mean_file = fullfile(input_dir, ['mean', input_name, '.nii']);
        motion_file = fullfile(input_dir, ['rp_', input_name, '.txt']);

        if exist(realigned_file, 'file')
            result.realigned_files{end+1} = realigned_file;
        else
            result.warnings{end+1} = ['Expected realigned file not found: ', realigned_file];
        end

        if exist(mean_file, 'file')
            result.mean_file = mean_file;
        else
            result.warnings{end+1} = ['Expected mean file not found: ', mean_file];
        end

        if exist(motion_file, 'file')
            result.motion_parameter_file = motion_file;
        else
            result.warnings{end+1} = ['Expected motion parameter file not found: ', motion_file];
        end

        if isempty(result.realigned_files)
            error('SPM realign did not produce realigned output.');
        end

        if isempty(result.motion_parameter_file)
            error('SPM realign did not produce motion parameter file.');
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
