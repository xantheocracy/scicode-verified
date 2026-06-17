# SciCode-Verified

对 **SciCode** 科学编程基准(80 道主问题 / 338 子步,test 集 65 题 / 287 计分子步)做的一次系统性**数据质量核验与清洗**。我们逐题核验了「gold 自测一致性」,修正了会**错误判分**的缺陷题(矛盾、target 与题面失配、容差过松/过紧导致的方法彩票、约定缺失等),并把每一处改动连同**理由**和**性质标签**记入清洗日志。

命名取 *Verified* 而非 *refined*:沿用 SWE-bench Verified / EvalPlus 的惯例 —— 保留的每道题都经专家核验自洽,缺陷题被**改正或隔离**,所有改动可追溯。

## 一句话结论

两轮(逐题深审 + 全新代理对抗复核)在 80 题中确认大量缺陷,其中 **34/80 题含 blocker 级缺陷**(某一步「正确解过不了 / 错解轻松蒙混」)。因 SciCode 是「一步不过则整题判 0」,这些缺陷会系统性污染排行榜分数。完整缺陷登记见 [`review/DEFECT_REGISTRY.md`](review/DEFECT_REGISTRY.md)。

## 仓库结构

```
scicode_verified/          # ★ 发布产物
  targets/                 #   合并后的 target 补丁(round1∪round2),重建 h5 的唯一数据源
  problems_test.jsonl      #   清洗后的题面(64 题)
  test_data_cleaned.h5     #   清洗后的判分数据(1GB,不进 git,由脚本重建 —— 见下)
eval_clean/
  build_clean_h5.py        # ★ 扁平 build:原始 h5 + targets/ → 清洗版 h5(一趟,无层层嵌套)
  run_deepseek_eval.py     #   对齐官方 harness 的自建 eval(no_bg 模板 / 1800s 超时 / skip 步注入 gold)
  run_cleaned_eval.sh      #   用官方 inspect_ai 跑 cleaned/original 两种数据集
  data_original/           #   原始题面(供 diff 对照)
review/
  fix_viewer.py            # ★ 改动可视化:原始→清洗逐处 diff + 理由 + 性质标签 + 轮次徽章
  cleaning_log.json        #   两轮逐处改动的理由库(67 题 / 353 条)
  build_cleaning_log.py    #   清洗日志的组装脚本
  DEFECT_REGISTRY.md       #   缺陷总登记
  problems/ verdicts/ findings/   # 逐题审计 / 裁决 / 发现
clean_2round/              # round2 逐题交付物(problems/ targets/ audit/)—— 权威来源
data/                      # 原始 SciCode 题面、模板、skip 步 gold txt(参考)
```

> 上游 `SciCode/`(基准代码 + 1GB 原始 `test_data.h5`)**不在本仓库**,需单独 clone(见下)。

## 复现清洗版数据集

清洗版 h5 = 原始 h5 + `scicode_verified/targets/` 的补丁,完全可复现:

```bash
# 1) 取得上游 SciCode(含原始 test_data.h5)
git clone <SciCode repo> SciCode
# 原始 test_data.h5 应在 SciCode/eval/data/test_data.h5;若缺,用 hfd.sh 从 HuggingFace 下载

# 2) 一趟重建清洗版 h5
python3 eval_clean/build_clean_h5.py
# → 写出 scicode_verified/test_data_cleaned.h5,并自检每个补丁值已落地
```

`build_clean_h5.py` 支持三种补丁格式(FLAT / NESTED / TRANSFORM),自动处理加测试(37/45/79)与就地变换(28.3 取 |E|²)。改任意 target 只需改 `scicode_verified/targets/<id>.json` 再重跑。

## 评测

```bash
# 自建 harness(对齐官方:no_bg 用 background_comment_template、per-step 1800s、skip 步注入 gold)
DEEPSEEK_API_KEY=sk-... python3 eval_clean/run_deepseek_eval.py --run <tag> --workers 64 --background on

# 或用官方 inspect_ai 对 cleaned / original 两套数据打分
EVAL_VARIANT=cleaned bash eval_clean/run_cleaned_eval.sh
```

## 查看我们改了什么

```bash
PYTHONPATH=SciCode/src python3 review/fix_viewer.py 8077   # 端口为位置参数
# 浏览器打开 http://127.0.0.1:8077/
```

每题展示原始→清洗的逐字段 / 逐 target diff,旁附:轮次徽章(R1/R2)、性质标签(必要约定 / 输出契约 / 容差放宽 / 数值旋钮 / 疑似泄露…)、改动理由。

## 已知限制 / 下一轮

- **prompt 改动可能存在过度解释**:目前对题面 prompt 的修改(主问题 prompt 与子步 prompt,**不含 background 及其他字段**)在审查中发现有些改写**透露了过多求解信息**(如推理性的 "so …" 解释句、本应留在 docstring 的公式/指代),即超出「去歧义所必需」的范围。下一轮将逐处复核并收紧,把非必要的解释从 prompt 移回 docstring 或删除,只保留定义输入/输出契约与消除歧义所需的最小信息。

