#!/bin/bash
# gen.sh <outfile> <promptfile> — 用 codex exec 出一张 UI 设计稿并落盘（复用 concepts_v2 已验证路径）
set -u
REPO=/Users/hhh0x/chuifnegji/puzhi-fan
OUTDIR=$REPO/design/workbench/mockups
OUT="$1"
PROMPTFILE="$2"
cd "$REPO"
codex exec --skip-git-repo-check -s workspace-write \
  "Use your built-in image generation tool to generate ONE image with EXACTLY this prompt (do not rewrite or shorten it):

$(cat "$PROMPTFILE")

After the image is generated, copy the generated PNG file from your generated_images output directory to exactly this path: $OUTDIR/$OUT
Then reply with just: DONE $OUT"
