# SciCode-Verified

对 **SciCode** 科学编程基准(80 道主问题 / 338 子步,test 集 65 题 / 287 计分子步)做的一次系统性**数据质量核验与清洗**。我们逐题核验了「gold 自测一致性」,修正了会**错误判分**的缺陷题(矛盾、target 与题面失配、容差过松/过紧导致的方法彩票、约定缺失等),并把每一处改动连同**理由**和**性质标签**记入清洗日志。

命名取 *Verified* 而非 *refined*:沿用 SWE-bench Verified / EvalPlus 的惯例 —— 保留的每道题都经专家核验自洽,缺陷题被**改正或隔离**,所有改动可追溯。

## 一句话结论

两轮(逐题深审 + 全新代理对抗复核)在 80 题中确认 **397 条缺陷**,其中 **34/80 题含 blocker 级缺陷**(某一步「正确解过不了 / 错解轻松蒙混」)。因 SciCode 是「一步不过则整题判 0」,这些缺陷会系统性污染排行榜分数。完整审计叙事 + 逐题/分轮明细见 [`CLEANING_LOG.md`](CLEANING_LOG.md);逐条决策见 [`ledger/`](ledger/)。

## 仓库结构

```
scicode_verified/          # ★ 发布产物(数据)
  problems/  targets/      #   SSOT:题面 + target 补丁(只改这里)
  problems_test.jsonl      #   派生:清洗后的题面(64 题)
  test_data_cleaned.h5     #   派生:判分数据(1GB,不进 git —— 从 Release 下载或脚本重建,见下)
  manifest.json            #   版本 + 每个文件 md5(消费端据此拒绝 stale 数据)
eval_clean/                # ★ 评测脚本
  run_deepseek_eval.py     #   对齐官方 harness 的自建 eval(no_bg 模板 / 1800s 超时 / skip 步注入 gold)
  build_clean_h5.py        #   扁平 build:原始 h5 + targets/ → 清洗版 h5(一趟,无层层嵌套)
  regrade_multienv.py      #   多环境(sci2024 + cp312)OR 打分,鲁棒于 numpy/scipy 漂移
  run_cleaned_eval.sh      #   用官方 inspect_ai 跑 cleaned/original 两种数据集
tools/                     # ★ 释放闸门
  assemble.py              #   SSOT → problems_test.jsonl + 刷新 manifest.json
  verify.py                #   双向 verify gate(见下)
ledger/                    #   决策账本:R3–R7.jsonl(逐条改动)+ BUG_*.md 深挖 + round6/ 延后项
CLEANING_LOG.md            #   清洗全过程的可读日志(方法 / 缺陷统计 / 分轮)
```

> 上游 `SciCode/`(基准代码 + 1GB 原始 `test_data.h5`)**不在本仓库**,仅重建 h5 时需要,单独 clone(见下)。

## 取得清洗版数据

**主路径 —— 从 GitHub Release 直接下载**(无需上游 SciCode / 无需重建):

```bash
# Release "data": test_data_cleaned.h5 + problems_test.jsonl + manifest.json
gh release download data -R flyingwagner/scicode-verified -D scicode_verified/
# 校验完整性(必须等于 manifest.json 的 h5_md5)
md5sum scicode_verified/test_data_cleaned.h5   # 2b41a7df40ddc23ce651ec05b8ecb6f8
```

**备用路径 —— 从原始 h5 本地重建**(清洗版 h5 = 原始 h5 + `scicode_verified/targets/` 补丁,完全可复现):

```bash
git clone <SciCode repo> SciCode      # 原始 test_data.h5 应在 SciCode/eval/data/;若缺用 hfd.sh 从 HuggingFace 下
python3 eval_clean/build_clean_h5.py  # → scicode_verified/test_data_cleaned.h5,并自检每个补丁值已落地
```

`build_clean_h5.py` 支持三种补丁格式(FLAT / NESTED / TRANSFORM),自动处理加测试(37/45/79)与就地变换(28.3 取 |E|²)。改任意 target 只需改 `scicode_verified/targets/<id>.json` 再重跑;重建结果必须复现 manifest 的 `h5_md5`。

## 评测

```bash
# 自建 harness(对齐官方:no_bg 用 background_comment_template、per-step 1800s、skip 步注入 gold)
DEEPSEEK_API_KEY=sk-... python3 eval_clean/run_deepseek_eval.py --run <tag> --workers 64 --background on
# 前沿模型走 openrouter(本地运行):OPENROUTER_API_KEY=... --model gpt-5.5|gemini-flash|opus-4.8 --background off

# 或用官方 inspect_ai 对 cleaned / original 两套数据打分
EVAL_VARIANT=cleaned bash eval_clean/run_cleaned_eval.sh
```

消费端启动即校验数据 md5 == `manifest.json`,不符**直接报错退出**,杜绝跑到 stale 数据。

## 清洗流程与校验闸门(verify-with-human)

为杜绝「逐题看过/改过、但没真正落进发布产物」这类 desync bug,本项目的清洗按
**verify-with-human** 这套纪律执行:**决策即数据 → 只由源组装 → 双向断言 → manifest 绑定消费**。

- **SSOT(唯一事实源)**:`scicode_verified/problems/<id>.json`(题面)+ `scicode_verified/targets/<id>.json`(target)。**只改这里**。
- **派生物**:`problems_test.jsonl`(由 `tools/assemble.py` 组装)、`test_data_cleaned.h5`(由 `eval_clean/build_clean_h5.py` 重建)。绝不手改。
- **决策账本**:每条批准的改动记一条 `ledger/<round>.jsonl`:`{id, field, before, after, verdict, reason, round}`。

```bash
python3 tools/assemble.py                            # SSOT -> jsonl + 刷新 manifest.json
python3 tools/verify.py --scope prompt --round R7    # 双向闸门,不过则 exit≠0,禁止发布
```

`verify.py` 强制:**已决必已发**(ledger.after 在 SSOT)、**已变必有据**(任何相对上版的改动都要有 ledger)、**耦合不变**(prompt 轮 targets md5 必须不变)、**语法可解**。

## 审计与决策记录

- 每处改动的**理由**与**分轮**:`ledger/R3–R7.jsonl` + `ledger/BUG_*.md`(#13 A_z 对称、#22 旋转符号等深挖)。
- 缺陷的**方法学与统计**(按受影响字段 × 评测模式、逐题 blocker、pattern library):`CLEANING_LOG.md`。
- 第一轮逐题 `findings/verdicts` 与详细缺陷登记表保留在 **git 历史**中(repo-tidy 提交时从工作树移除)。

## 许可

派生自 SciCode 基准(Apache-2.0);本清洗版数据据同一 Apache-2.0 许可再分发,更正与核验由 SciCode-Verified 作者完成。
