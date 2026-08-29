#!/bin/bash
# gen.sh <outfile> <prompt...> — 用 codex exec 出一张概念图并落盘
set -u
REPO=/Users/hhh0x/chuifnegji/puzhi-fan
OUT="$1"; shift
PROMPT="$*"
cd "$REPO"
codex exec --skip-git-repo-check -s workspace-write \
  "Use your built-in image generation tool to generate ONE image with EXACTLY this prompt (do not rewrite or shorten it):

$PROMPT

After the image is generated, copy the generated PNG file from your generated_images output directory to exactly this path: $REPO/concepts_v2/$OUT
Then reply with just: DONE $OUT"
