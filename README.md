# 包装温度剂量工作台

原生 HTML、CSS 和 JavaScript 工作台，业务计算由 Python 完成，使用本机 SQLite 持久化。无需安装前端依赖。仅用于本地合成样本，不对公网开放。

```sh
python3 -B -m workbench
```

浏览器打开命令输出的地址（默认 `http://127.0.0.1:8816`）。工作台支持样例与文件导入、发布历史、指定版本加工、对比、复算和证据导出。可用 `--port`、`--db` 指定本机端口和数据库文件。

新增领域加工：断档清单、平行校准复核、分段剂量账。流程验收：`python3 -B examples/workbench_check.py`。

### 双位置冷点剂量

在工作台运行 `cold-spot`。按同一包装内两个空间测点的逐时较低温度精确积分，保留交换时点和分段剂量界。演练：`python3 -B examples/workbench_check.py cold-spot`。

### 冷点分窗凭据

在工作台运行 `cold-windows`。在各作业窗内按真实测点覆盖截取响应积分，保留该窗的剂量界及来源切换。演练：`python3 -B examples/workbench_check.py cold-windows`。

### 双钟对时与剂量

在工作台运行 `clock-alignment`。按两次同步见证将内点记录映射到试验时钟，再按物理秒复查冷点剂量与覆盖。演练：`python3 -B examples/workbench_check.py clock-alignment`。

### 分页回传与检查点交接

记录器按试验标号和页号分页回传整秒温度记录。页受理回执持久化，试验台重启后仍有效，已确认的页不再要求重传；检查点交接是独立动作，只有影响该检查点的时间都有覆盖或丢失凭据时才交付可追查的值或区间，确失时段不搭桥、保留剂量上下界。演练：`python3 -B examples/paged_log_check.py`。

### 成品复核与交接

运行 `checkpoints` 后在结果中打开「查看复核交接」。合格成品可通过复核后签发；不合格成品可退回且保留原判定。发布新修订或恢复旧修订都会换代，已经通过但未签发的旧复核不能补签。已签凭据可从同一运行的历史复核中下载。

旧版工作台数据库打开时会在事务中自动升级到 SQLite 结构 v3，不改写原始录入、历史运行或证据。升级后的数据库不再由旧版工作台打开；保留旧版时请使用数据库的独立副本。

兼容保留原 HTTP 服务和数据格式，以下是原服务说明。

---

# 包装温度指示换算

包装试验记录员为模拟指示片指定响应曲线，并提交时间序列。服务生成分段暴露和判读证据，断档单列；这是数据处理演示，不是食品安全或运输判定工具。

## 运行

Python 3.11 或以上，仅标准库。切换到此仓库目录。

```sh
python3 -B -m thermal.http_api --port 8743
curl --json @examples/demo.json http://127.0.0.1:8743/indicator/rate-windows
```

不常驻启动也可运行以下演示；每次使用临时本机端口，结束后释放。

```sh
python3 -B -m thermal.example /indicator/dose
python3 -B -m thermal.example /indicator/disposition
python3 -B -m thermal.example /indicator/rate-windows
```

参见 [领域规则与接口](PROJECT_SPEC.md)。`examples/demo.json` 为完整合成输入；其他示例用于观察拒收或待核。业务单元测试留待后续，当前不假设联网、数据库或已有用户数据。

### 累计剂量检查点

发布更新后的 `examples/workbench.json`，在结果区选择「累计剂量检查点」。验收命令：`python3 -B examples/workbench_check.py checkpoints`。这项加工可选；老原料不含 `inspection_seconds` 时仍可使用原操作。
