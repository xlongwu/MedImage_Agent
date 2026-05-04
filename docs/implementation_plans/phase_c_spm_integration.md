# Phase C：真实 SPM 联调

> 目标版本：v0.3.0-alpha | 预计工期：3–4 周 | 前置条件：Phase A 封版完成，有 MATLAB + SPM12 环境

---

## 1. 目标与范围

在真实 MATLAB/SPM12 环境中，用 synthetic BIDS 数据跑通完整的 SPM 预处理链路（Slice Timing → Realign → Coregister → Segment → Normalize → Smooth），每个节点验证通过后再串联。

**不做**：真实临床数据、DPABI 全流程、GPU 加速、多 subject 批量处理。

---

## 2. 前置条件检查

- [ ] MATLAB R2020b+ 已安装，`matlab -batch "disp('hello')"` 可执行
- [ ] SPM12 存在于 `third_party/spm12/`
- [ ] `python -m backend.app.tools.check_env_cli` 通过
- [ ] `python -m backend.app.tools.run_spm_smoke_cli` 通过

---

## 3. 新增/修改文件清单

```text
matlab/spm_check_env.m                        # 修改：强化环境检查
backend/app/tools/spm_runner.py               # 修改：增强 SPM 调用
backend/app/tools/spm_slice_timing_runner.py  # 修改：dry-run + approve 模式
backend/app/tools/spm_realign_runner.py       # 修改：dry-run + approve 模式
backend/app/tools/spm_coregister_runner.py    # 修改：dry-run + approve 模式
backend/app/tools/spm_segment_runner.py       # 修改：dry-run + approve 模式
backend/app/tools/spm_normalize_runner.py     # 修改：dry-run + approve 模式
backend/app/tools/spm_smooth_runner.py        # 修改：dry-run + approve 模式
backend/app/tools/spm_chain_validator.py      # 新增：链式验证工具
backend/app/api/routes.py                     # 修改：新增链式验证端点
reports/spm_chain_validation/                 # 新增：验证报告目录
```

---

## 4. 逐步实施步骤

### Step 1：强化 MATLAB/SPM 环境检查

每个 SPM runner 在真实执行前必须回答 5 个问题：

```
1. MATLAB 是否存在？       → check_env_cli
2. MATLAB 版本？           → matlab -batch "version"
3. SPM 是否在 path？       → matlab -batch "which spm"
4. SPM 版本？             → matlab -batch "spm('version')"
5. SPM batch 是否可运行？  → smoke test: matlab -batch "spm_jobman('initcfg')"
```

输出文件：
```text
work/environment/matlab_check.json
work/environment/spm_check.json
work/environment/spm_smoke_test.json
```

### Step 2：单节点验证（按顺序）

每个节点必须支持 3 种执行模式：

```text
Mode 1: dry_run     → 生成 MATLAB script, 不执行
Mode 2: synthetic_execute → 执行 synthetic BIDS, approved=true required
Mode 3: approved_execute  → 执行任意数据, approved=true + input_whitelist required
```

验证顺序（按依赖关系）：

```
1. Slice Timing      → 输入: synthetic BOLD + SliceTiming 参数 → 输出: a{BOLD}.nii
2. Realignment       → 输入: a{BOLD}.nii                    → 输出: rp_*.txt, r{BOLD}.nii, mean{BOLD}.nii
3. Coregistration    → 输入: mean{BOLD}.nii + T1w.nii       → 输出: coreg_T1w.nii
4. Segmentation      → 输入: coreg_T1w.nii                  → 输出: c1-c6 T1w.nii
5. Normalization     → 输入: r{BOLD}.nii + c1-c6 T1w.nii   → 输出: w{BOLD}.nii
6. Smoothing         → 输入: w{BOLD}.nii                    → 输出: s{BOLD}.nii
```

每个节点验证的通用流程：

```python
# 伪代码
def validate_spm_node(node_id, input_files, params):
    # 1. 检查 MATLAB 和 SPM 可用
    # 2. 构造 matlabbatch
    # 3. dry_run: 写出 .m 文件
    # 4. synthetic_execute: 用 synthetic BIDS 真实运行
    # 5. 检查输出文件是否存在且可读
    # 6. 运行对应 QC
    # 7. 返回 node_validation_result.json
```

每个节点的交付物：
```text
work/spm_validation/{node_id}/
  ├── matlabbatch.m
  ├── matlab_stdout.log
  ├── matlab_stderr.log
  ├── node_result.json
  ├── node_qc.json
  └── node_validation_report.md
```

### Step 3：SPM Chain 验证

单节点全部通过后，验证完整链：

```text
synthetic BIDS
  → Slice Timing
  → Realignment
  → Coregistration
  → Segmentation
  → Normalization
  → Smoothing
```

链式验证要点：
- 每个节点的输出自动成为下一个节点的输入
- 任意节点失败即停止（`stop_on_failure: true`）
- 每一步的结果和 QC 都记录

API 端点：
```text
POST /api/spm/chain/validate
GET  /api/spm/chain/validation-results
```

---

## 5. 安全边界（强制执行）

```
禁止：
  ✗ 直接修改 rawdata
  ✗ 覆盖已有 derivatives（除非 allow_overwrite=true + approved=true）
  ✗ 无审批运行（approved 必须显式为 true）
  ✗ 自动 batch 多 subject
  ✗ 自动调用 DPABI/DPARSF

允许：
  ✓ 只读 rawdata
  ✓ 写入 derivatives/ / work/ / logs/ / reports/
  ✓ dry_run 模式生成 MATLAB script
  ✓ synthetic_execute 模式（需 approved=true）
```

---

## 6. API 端点设计

```text
# 环境检查
POST /api/spm/check-env              → 强化版环境检查
GET  /api/spm/check-env/status       → 查看环境状态

# 单节点验证
POST /api/spm/validate/{node_id}     → 验证单个 SPM 节点
GET  /api/spm/validate/{node_id}/status/{run_id} → 查看验证状态

# 链式验证
POST /api/spm/chain/validate         → 启动完整链验证
GET  /api/spm/chain/status/{run_id}  → 查看链验证状态
GET  /api/spm/chain/results          → 查看所有链验证结果
```

---

## 7. 验收标准

- [ ] `check_env_cli` 明确报告 MATLAB/SPM 状态
- [ ] 无 MATLAB 时安全失败（不崩溃）
- [ ] MATLAB 存在但 SPM 不存在时给出明确错误
- [ ] 6 个 SPM 单节点 dry_run 模式可生成有效的 `.m` 文件
- [ ] 6 个 SPM 单节点 synthetic_execute 模式可产出正确 NIfTI
- [ ] Slice Timing 输出 `a{BOLD}.nii`
- [ ] Realignment 输出 `rp_*.txt` + `r{BOLD}.nii`
- [ ] Coregistration 输出 `coreg_T1w.nii`
- [ ] Segmentation 输出 `c1-c6 T1w.nii`
- [ ] Normalization 输出 `w{BOLD}.nii`
- [ ] Smoothing 输出 `s{BOLD}.nii`
- [ ] SPM 链式验证可从 BIDS 到 Smooth 完整跑通
- [ ] 每个节点有 result JSON + QC JSON + MATLAB script snapshot
- [ ] 所有输出在 derivatives/ 和 work/ 中，不写入 rawdata
- [ ] 链式验证报告写入 `reports/spm_chain_validation/`
