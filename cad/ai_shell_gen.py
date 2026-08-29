#!/usr/bin/env python3
"""LiteCool S1 — AI 外观皮肤(图生3D)驱动。支持两个后端:

  --backend hunyuan  腾讯混元 Pro(ai3d,积分制;2026-08-29 实测账号积分尽,ResourceInsufficient)
  --backend meshy    Meshy image-to-3d(本机 Keychain 有 key,余额实测 905;含贴图 15cr/次实测)

凭证:绝不进 repo/日志。hunyuan 走 ~/.config/hunyuan/credentials 或环境变量;
meshy 走 macOS Keychain(service 名见 MESHY_KEY_SERVICE,与 kiln/jxx 项目同一约定)。

用法:
  python3 cad/ai_shell_gen.py --backend meshy --image concepts_v2/A_1.png --dir cad/ai_shell_a
  python3 cad/ai_shell_gen.py --backend hunyuan --image concepts_v2/A_1.png --dir cad/ai_shell_a \
      [--model 3.1] [--faces 80000] [--pbr]

产物布局(<dir>/):
  input/concept.png  api/submit.json  api/query.json(含积分)  api/result_urls.txt
  raw/hunyuan_raw.glb|meshy_raw.glb   manifest.json
"""
import argparse
import base64
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

MESHY_API = "https://api.meshy.ai/openapi/v1"
MESHY_KEY_SERVICE = "threejs-dreamfall.meshy.api-key"

SKILL_SCRIPTS = os.path.expanduser("~/.agents/skills/hunyuan-3d/scripts")


def curl_download(url, out_path, attempts=8):
    """大文件慢链:断点续传重试(curl --retry 不续传,exit 18 会丢进度)。"""
    for i in range(attempts):
        r = subprocess.run(["curl", "-sS", "-L", "-C", "-", "--retry", "3",
                            "-o", out_path, url])
        if r.returncode == 0:
            return
        print("  curl exit %s,resume %d/%d" % (r.returncode, i + 1, attempts), file=sys.stderr)
        time.sleep(3)
    sys.exit("下载失败(续传 %d 次仍断): %s" % (attempts, out_path))


# ---------------- Meshy ----------------
def meshy_key():
    return subprocess.run(
        ["security", "find-generic-password", "-s", MESHY_KEY_SERVICE, "-w"],
        capture_output=True, text=True, check=True).stdout.strip()


def meshy_call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(MESHY_API + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + meshy_key())
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"raw": raw}


def run_meshy(args, d):
    _, bal_before = meshy_call("GET", "/balance")
    mime = mimetypes.guess_type(args.image)[0] or "image/png"
    with open(args.image, "rb") as f:
        uri = "data:%s;base64," % mime + base64.b64encode(f.read()).decode()
    body = {
        "image_url": uri,
        "should_texture": True,
        "enable_pbr": bool(args.pbr),
        "texture_resolution": "2k",
        "topology": args.topology,
        "origin_at": "bottom",
    }
    if args.faces:
        body["target_polycount"] = args.faces
        body["should_remesh"] = True
    status, resp = meshy_call("POST", "/image-to-3d", body)
    recorded = dict(body)
    recorded["image_url"] = "<data uri %d chars>" % len(uri)
    with open(os.path.join(d, "api", "submit.json"), "w") as f:
        json.dump({"http": status, "request": recorded, "response": resp},
                  f, ensure_ascii=False, indent=2)
    if status not in (200, 202):
        sys.exit("meshy submit 失败 HTTP %s: %s" % (status, json.dumps(resp)[:400]))
    tid = resp.get("result") or resp.get("id")
    print("meshy task=%s polling..." % tid, file=sys.stderr)

    final = {}
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        _, q = meshy_call("GET", "/image-to-3d/%s" % tid)
        st = q.get("status")
        print("  status=%s progress=%s" % (st, q.get("progress")), file=sys.stderr)
        if st in ("SUCCEEDED", "FAILED", "CANCELED"):
            final = q
            break
        time.sleep(args.interval)
    else:
        sys.exit("轮询超时 task=%s" % tid)
    with open(os.path.join(d, "api", "query.json"), "w") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    if st != "SUCCEEDED":
        sys.exit("meshy 任务 %s: %s" % (st, final.get("task_error")))

    urls = final.get("model_urls") or {}
    with open(os.path.join(d, "api", "result_urls.txt"), "w") as f:
        for k, v in urls.items():
            f.write("%s\t%s\n" % (k, v))
    glb_url = urls.get("glb")
    if not glb_url:
        sys.exit("SUCCEEDED 但无 glb: " + json.dumps(list(urls)))
    out_glb = os.path.join(d, "raw", "meshy_raw.glb")
    curl_download(glb_url, out_glb)

    _, bal_after = meshy_call("GET", "/balance")
    manifest = {
        "backend": "meshy",
        "task_id": tid,
        "image": args.image,
        "params": recorded,
        "consumed_credits": final.get("consumed_credits"),
        "balance_before": (bal_before or {}).get("balance"),
        "balance_after": (bal_after or {}).get("balance"),
        "polycount_reported": final.get("polycount"),
        "raw_glb": "raw/meshy_raw.glb",
        "raw_glb_bytes": os.path.getsize(out_glb),
    }
    return manifest


# ---------------- Hunyuan ----------------
def run_hunyuan(args, d):
    sys.path.insert(0, SKILL_SCRIPTS)
    from hunyuan3d_gen import call, _encode_file

    payload = {
        "Model": args.model,
        "ImageBase64": _encode_file(args.image),
        "GenerateType": args.type,
        "FaceCount": args.faces,
        "EnablePBR": bool(args.pbr),
    }
    sub = call("SubmitHunyuanTo3DProJob", payload)
    with open(os.path.join(d, "api", "submit.json"), "w") as f:
        json.dump(sub, f, ensure_ascii=False, indent=2)
    job = sub.get("JobId")
    if not job:
        sys.exit("提交未返回 JobId: " + json.dumps(sub, ensure_ascii=False))
    print("JobId=%s polling..." % job, file=sys.stderr)

    query = {}
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        query = call("QueryHunyuanTo3DProJob", {"JobId": job})
        status = str(query.get("Status") or "")
        print("  status=%s" % status, file=sys.stderr)
        if status.upper() == "DONE":
            break
        if status.upper() == "FAIL":
            with open(os.path.join(d, "api", "query.json"), "w") as f:
                json.dump(query, f, ensure_ascii=False, indent=2)
            sys.exit("任务 FAIL: " + json.dumps(query, ensure_ascii=False))
        time.sleep(args.interval)
    else:
        sys.exit("轮询超时,JobId=%s" % job)

    with open(os.path.join(d, "api", "query.json"), "w") as f:
        json.dump(query, f, ensure_ascii=False, indent=2)
    files = query.get("ResultFile3Ds") or []
    with open(os.path.join(d, "api", "result_urls.txt"), "w") as f:
        for it in files:
            f.write("%s\t%s\n" % (it.get("Type", ""), it.get("Url", "")))
    glb_url = next((it["Url"] for it in files if (it.get("Type") or "").upper() == "GLB"), None)
    if not glb_url:
        sys.exit("DONE 但无 GLB 产物: " + json.dumps(files, ensure_ascii=False))
    out_glb = os.path.join(d, "raw", "hunyuan_raw.glb")
    curl_download(glb_url, out_glb)
    manifest = {
        "backend": "hunyuan",
        "job_id": job,
        "image": args.image,
        "params": {"Model": args.model, "GenerateType": args.type,
                   "FaceCount": args.faces, "EnablePBR": bool(args.pbr)},
        "credit_consumed": query.get("ResultCreditConsumed"),
        "credit_details": query.get("ResultCreditDetails"),
        "raw_glb": "raw/hunyuan_raw.glb",
        "raw_glb_bytes": os.path.getsize(out_glb),
    }
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=("hunyuan", "meshy"), default="meshy")
    ap.add_argument("--image", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--model", default="3.1", help="hunyuan: 3.0/3.1")
    ap.add_argument("--faces", type=int, default=0,
                    help="hunyuan: FaceCount;meshy: target_polycount(0=不重拓扑,保最高细节)")
    ap.add_argument("--pbr", action="store_true")
    ap.add_argument("--type", default="Normal", help="hunyuan GenerateType")
    ap.add_argument("--topology", default="triangle", choices=("triangle", "quad"),
                    help="meshy 拓扑")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--interval", type=int, default=15)
    args = ap.parse_args()

    d = args.dir
    for sub in ("input", "api", "raw"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    shutil.copy2(args.image, os.path.join(d, "input", "concept.png"))

    manifest = run_meshy(args, d) if args.backend == "meshy" else run_hunyuan(args, d)
    with open(os.path.join(d, "manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
