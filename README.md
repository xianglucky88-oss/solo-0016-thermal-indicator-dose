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
