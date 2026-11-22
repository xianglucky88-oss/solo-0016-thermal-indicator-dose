# 包装温度剂量工作台

原生 HTML、CSS 和 JavaScript 工作台，业务计算由 Python 完成，使用本机 SQLite 持久化。无需安装前端依赖。仅用于本地合成样本，不对公网开放。

```sh
python3 -B -m workbench
```

浏览器打开命令输出的地址（默认 `http://127.0.0.1:8816`）。工作台支持样例与文件导入、发布历史、指定版本加工、对比、复算和证据导出。可用 `--port`、`--db` 指定本机端口和数据库文件。

新增领域加工：断档清单、平行校准复核、分段剂量账。流程验收：`python3 -B examples/workbench_check.py`。

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
