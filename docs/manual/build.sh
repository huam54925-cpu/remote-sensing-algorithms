#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p output/pdf tmp/pdfs/manual-build
for pass in 1 2 3; do
  xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error \
    -output-directory=tmp/pdfs/manual-build \
    docs/manual/operations-manual.tex \
    > "tmp/pdfs/manual-build/pass-$pass.stdout" 2>&1
done
cp tmp/pdfs/manual-build/operations-manual.pdf \
  output/pdf/remote-sensing-operations-manual.pdf
sha256sum output/pdf/remote-sensing-operations-manual.pdf \
  > output/pdf/remote-sensing-operations-manual.pdf.sha256
printf 'PDF: %s/output/pdf/remote-sensing-operations-manual.pdf\n' "$PWD"
