# SciCode Review — Batch 1 总结(题 1–20)

20 个 fable 代理逐题深审,每题产出 `review/findings/<id>.json`。
环境:numpy 2.2.6 / scipy 1.15.2(现代环境;SciCode 原生于 numpy 1.x 时代)。

## 总量

- **75 个 finding**:7 blocker / 38 major / 30 minor
- 缺陷类型分布:D4 约定不明 ×23,D10 文档矛盾 ×19,D8 测试过弱 ×14,D2 无法做出 ×4,D7 target 错 ×4,D9 跨步依赖 ×4,D1 签名不匹配 ×3,D6 容差 ×3,D3 单位 ×1
- **5 道题含 blocker(全部在 test split)**:2、5、13、17、18
- dev 题(1,3,4,6,7,10,19)gold 全部通过官方判分 → 与此前 gold 审计一致;但 gold 通过 ≠ 无缺陷(见 19.1)

## Blocker 明细(已逐条人工复核证据)

| 题.步 | 类型 | 问题 |
|---|---|---|
| 2.1 | D2×2, D7 | `required_dependencies` 用了 scipy≥1.14 已删除的 `simps` → 现代环境下**任何解都 0 分**;且 target 是 (61,51) 极坐标网格而 docstring 说返回笛卡尔 x-y;观察面位置/径向范围/归一化全部未说明 |
| 5.1 | D6, D7 | test 1 输入恰好触发 Lanczos 精确 breakdown(Krylov 维数 4 < 需要的 6),target 后两列是某次运行的浮点噪声,**8 种教科书正确实现全挂**;target 自身违反"正交列"规格(QᵀQ−I 偏差 0.945) |
| 13.12 | D9 | target 不是演化后场的约束值,而是**ICN 积分器第二中间级**的值——只有完全复刻 gold 内部中间变量才能过 |
| 17.2 | D7 | 四面体 DOS 的 target 与 background 给的公式算出的值不符(0.40 vs 0.125 等;解析+几何+2000 万点 MC 三方验证) |
| 18.2 | D7 | test 0 给 `w=[0]`(需要 28 个权重),正确实现直接 IndexError;target [0.5,1.0] 是非有理 B 样条值,与输入不自洽 |

## 复发模式(进 skill v2)

1. **依赖漂移(新 D12)**:`simps` 在题 2、28(28 未审,全量扫描发现)→ 审题第 0 步先 `exec(required_dependencies)`
2. **空参数 header**:`def tensor():` 配 `tensor([0,1],[0,1])` 调用(11.1 `ket(dim)`、11.3、19.1)——用户报过的原始缺陷类,数据级实锤
3. **1-based vs 0-based 下标未声明**(11.4/11.8/11.9,量子信息题系 QETLAB 传统 1-based)
4. **顺序/符号约定未声明**(10.2 行序、10.3 位移符号、10.6 recvec 是否含 2π)
5. **跨步顺序敏感**(10.7):上一步测试对顺序不敏感(set 比较),下一步按位置消费其输出 → 合规实现也挂
6. **退化 target**(7.1、10.10 全零;2 的 test4):`np.zeros` 就能过 → D8 标准探针:跑 trivial 实现验证
7. **隐藏随机种子/统计断言**(14.1 测试里偷偷 `seed(0)`、14.2 无种子统计检验 ~5% 天然翻车率)
8. **容差盲区**(15.1 对角虚部不受约束、16.2 二阶效应低于 rtol)
9. **诱饵参数/重复测试**(2:d=4 与 d=2 的 target 全同)→ 检查同步内 test 间 target 是否两两相同
10. **测试间变量泄漏**:官方 harness 把所有 test 拼一个脚本(共享命名空间)。工具已改:默认 joint(官方行为),`--isolate` 仅用于定位
11. **题面常数损坏**(15.2 约化普朗克常数写错)→ 题面数值常数做量纲/数值 sanity check

## 工具修正记录

- `steptest.py` 默认模式改为 joint(= 官方拼接行为),新增 `--isolate` 诊断模式。原逐 test 隔离会产生假 FAIL(题 7 test4 的 NameError 在官方模式下不存在)

## 校准结论(代理质量)

- dev 题上代理结论与 gold 审计 100% 一致(无假 blocker);抽查 5 个 blocker + 3 个 D1 全部人工复核属实
- 注意:per-test 隔离造成过 1 例假 partial(题 7),已修工具并写入 v2 协议
