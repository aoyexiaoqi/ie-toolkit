# ie-toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

面向制造业工艺 / 工业工程师的命令行计算工具：节拍时间（Takt Time）、设备综合效率（OEE）、产线平衡（Line Balancing）与产能（Capacity）。每个子命令都打印输入、公式和结果，方便核对；加 `--json` 可输出机器可读结果，供脚本或其他工具调用。

[English](#english)

## 安装

```bash
pip install git+https://github.com/aoyexiaoqi/ie-toolkit.git
```

从源码安装：

```bash
git clone https://github.com/aoyexiaoqi/ie-toolkit.git
cd ie-toolkit
pip install .
```

需要 Python 3.9 及以上版本，无第三方运行时依赖。安装后命令名为 `ie-calc`，也可以用 `python -m ie_toolkit` 调用。

## 用法

### 1. 节拍时间 takt

公式：

```text
总可用时间 = 每班可用时间 × 班次
节拍时间（s/件） = 总可用时间 / 需求量
生产速率（件/小时） = 3600 / 节拍时间
```

`--available` 为每班净可用生产时间（秒，已扣除休息等计划停机），`--demand` 为该期间需求量（件），`--shifts` 为班次（默认 1）。

```bash
ie-calc takt --available 27000 --demand 450
```

```text
Inputs:
  Available time per shift: 27000.0 s
  Shifts: 1
  Total available time: 27000.0 s
  Demand: 450.0 units
Formula:
  Takt time = total available time / demand = 27000.0 / 450.0
Result:
  Takt time: 60.00 s/unit
  Rate: 60.00 units/hour
```

### 2. 设备综合效率 oee

公式：

```text
运行时间 = 计划时间 − 停机时间
时间开动率 Availability = 运行时间 / 计划时间
性能开动率 Performance = （理想节拍 × 总产量） / 运行时间（秒）
质量合格率 Quality = 良品数 / 总产量
OEE = Availability × Performance × Quality
```

`--planned`、`--downtime` 单位为分钟，`--ideal-cycle` 单位为秒/件。

```bash
ie-calc oee --planned 480 --downtime 30 --ideal-cycle 50 --total 500 --good 480
```

```text
Inputs:
  Planned time: 480.0 min
  Downtime: 30.0 min
  Runtime: 450.0 min
  Ideal cycle: 50.0 s
  Total count: 500
  Good count: 480
Formula:
  Availability = runtime / planned = 450.0 / 480.0
  Performance = (ideal cycle x total) / runtime in seconds = (50.0 x 500) / 27000.0
  Quality = good / total = 480 / 500
  OEE = Availability x Performance x Quality
Result:
  Availability: 93.75%
  Performance: 92.59%
  Quality: 96.00%
  OEE: 83.33%
```

### 3. 产线平衡 balance

公式：

```text
总作业内容 = Σ 各工位节拍
瓶颈工位 = 节拍最大的工位
线平衡率 Line efficiency = 总作业内容 / （工位数 × 瓶颈节拍）
每周期空闲时间 = 工位数 × 瓶颈节拍 − 总作业内容
理论最少工位数 = ceil（总作业内容 / 节拍时间）
```

`--stations` 为逗号分隔的各工位节拍（秒），`--takt` 为要求的节拍时间（秒）。输出还会列出超过节拍的工位。

```bash
ie-calc balance --stations 12.5,10.2,15.0 --takt 20
```

```text
Inputs:
  Station cycle times: 12.5, 10.2, 15 s
  Takt time: 20 s
Formula:
  Line efficiency = total work content / (stations x bottleneck) = 37.7 / (3 x 15)
  Idle time per cycle = stations x bottleneck - total work content
  Theoretical min stations = ceil(total work content / takt)
Result:
  Total work content: 37.7 s
  Bottleneck: station 3 at 15 s
  Line efficiency: 83.78%
  Idle time per cycle: 7.3 s
  Theoretical min stations: 2
  Within takt: yes (every station <= takt)
```

### 4. 产能 capacity

公式：

```text
毛产能（件） = floor（可用时间 / 节拍）
良品产能（件） = floor（毛产能 × 良率）
```

`--yield` 为一次通过率（0 到 1 之间的小数，默认 1.0）。

```bash
ie-calc capacity --cycle 30 --available 27000 --yield 0.98
```

```text
Inputs:
  Cycle time: 30.0 s/unit
  Available time: 27000.0 s
  Yield: 0.98
Formula:
  Gross units = floor(available / cycle) = floor(27000.0 / 30.0)
  Good units = floor(gross units x yield)
Result:
  Gross units: 900
  Good units: 882
```

### JSON 输出

所有子命令都支持 `--json`：

```bash
ie-calc takt --available 27000 --demand 450 --json
```

```json
{
  "command": "takt",
  "available_seconds": 27000.0,
  "shifts": 1,
  "total_available_seconds": 27000.0,
  "demand_units": 450.0,
  "takt_seconds_per_unit": 60.0,
  "units_per_hour": 60.0
}
```

## 校验与退出码

输入不合法时会在 stderr 给出明确错误并以退出码 `2` 退出（参数缺失等 argparse 错误同样为 `2`，正常计算为 `0`）。被拒绝的情况包括：需求量 / 节拍 / 可用时间非正、停机时间大于计划时间、良品数大于总产量、工位列表格式错误（空项、非数字、非正数）、良率不在 (0, 1] 区间内。例如：

```bash
$ ie-calc oee --planned 480 --downtime 500 --ideal-cycle 50 --total 500 --good 480
error: downtime must not exceed planned time
```

## 注意

本工具只做公式计算，结果是**计算辅助**：节拍、OEE、平衡率和产能是否可用，取决于输入数据（可用时间口径、理想节拍取值、停机分类、良率统计周期等）是否符合现场实际。输入口径与假设始终由工程师本人负责确认，工具不对基于结果做出的工艺与排产决策负责。

## 开发

```bash
pip install -e ".[test]"
pytest            # 运行测试
pytest --cov=ie_toolkit --cov-report=term-missing
```

## English

**ie-toolkit** is a command-line calculator for manufacturing / industrial engineers, providing four subcommands under the `ie-calc` command:

- `ie-calc takt --available SECONDS --demand UNITS [--shifts N]` — takt time = total available time / demand, plus units per hour.
- `ie-calc oee --planned MINUTES --downtime MINUTES --ideal-cycle SECONDS --total COUNT --good COUNT` — OEE = Availability × Performance × Quality, each shown as a percentage.
- `ie-calc balance --stations 12.5,10.2,15.0 --takt 20` — total work content, bottleneck station, line efficiency, idle time per cycle, theoretical minimum stations, and stations violating takt.
- `ie-calc capacity --cycle SECONDS --available SECONDS [--yield 0.98]` — gross units = floor(available / cycle); good units apply the yield.

Every subcommand prints its inputs, the formula, and the result, and accepts `--json` for machine-readable output. Invalid inputs (non-positive demand/cycle/available time, downtime over planned time, good count over total count, malformed station lists, yield outside (0, 1]) are rejected with a clear error message and exit code 2. Requires Python 3.9+, no third-party runtime dependencies, MIT license.

Note: results are calculation aids only — the inputs and assumptions behind them remain the engineer's responsibility.

## License

MIT
