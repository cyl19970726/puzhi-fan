"""pipeline/run.py — 流水线 CLI。

用法:
  python3 pipeline/run.py status    # 生成 data/pipeline_status.json 并打印各阶段状态
  python3 pipeline/run.py validate  # 跑数据完整度闸 → data/validation_report.json
  python3 pipeline/run.py build     # validate → status → 调 workbench/build.py 生成工作台

注意: validate 有 fail 不阻断 build —— G-数据闸的语义是「呈现层渲染待补占位」，
不是「不许构建」。闸结果会原样呈现在工作台流水线总览里。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import status  # noqa: E402
import validate  # noqa: E402


def cmd_validate():
    report = validate.run_checks()
    validate.os.makedirs(validate.os.path.dirname(validate.REPORT_PATH), exist_ok=True)
    with open(validate.REPORT_PATH, "w", encoding="utf-8") as f:
        validate.json.dump(report, f, ensure_ascii=False, indent=2)
    s = report["summary"]
    print("validate: %d pass / %d warn / %d fail" % (s["pass"], s["warn"], s["fail"]))
    for c in report["checks"]:
        if c["level"] != "pass":
            print("  [%s] %s: %s" % (c["level"].upper(), c["id"],
                                     "; ".join(c["missing"][:3]) + (" …" if len(c["missing"]) > 3 else "")))
    return report


def cmd_status(report=None):
    st = status.build_status(report)
    with open(status.STATUS_PATH, "w", encoding="utf-8") as f:
        status.json.dump(st, f, ensure_ascii=False, indent=2)
    for s in st["stages"]:
        print("%s %-8s %s %s" % (s["id"], s["name"], s["status_label"],
                                 ("— " + s["note"]) if s["note"] else ""))
    return st


def cmd_build():
    report = cmd_validate()
    cmd_status(report)
    # 调 workbench/build.py（它内部会重新消费 validation_report / pipeline_status）
    wb_dir = os.path.join(status.REPO_ROOT, "workbench")
    sys.path.insert(0, wb_dir)
    import importlib
    build = importlib.import_module("build")
    return build.main()


USAGE = __doc__.strip()


def main(argv):
    if len(argv) < 2 or argv[1] not in ("status", "validate", "build"):
        print(USAGE)
        return 2
    cmd = argv[1]
    if cmd == "validate":
        cmd_validate()
        return 0
    if cmd == "status":
        cmd_status()
        return 0
    return cmd_build() or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
