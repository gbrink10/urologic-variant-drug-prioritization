"""Single place where every path in the pipeline is resolved.

The v26-v28 scripts each hard-coded absolute paths on the author's machine,
which meant the deposited code could not run anywhere else - a fair criticism of
a manuscript whose contribution is that its analysis can be audited.

Everything is now relative to the repository root, with environment-variable
overrides for the two directories a user might legitimately want elsewhere:

    UVDP_FIGURES   where figures are written   (default <repo>/figures)
    UVDP_OUTPUT    where documents are written (default <repo>/output)

Nothing here needs to be edited to run the pipeline on another machine.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

DATA = REPO / 'data'
RAW = DATA / 'raw_matrices'
PREPARED = DATA / 'prepared'
DE_RESULTS = DATA / 'DE_results'
RESULTS = REPO / 'results'
REFIT = RESULTS / 'refit'
CODE = REPO / 'code'

FIGURES = Path(os.environ.get('UVDP_FIGURES', REPO / 'figures'))
PANEL_C = FIGURES / 'panelC'
OUTPUT = Path(os.environ.get('UVDP_OUTPUT', REPO / 'output'))

for _d in (DATA, RESULTS, REFIT, FIGURES, OUTPUT):
    _d.mkdir(parents=True, exist_ok=True)


def describe():
    return {
        'REPO': str(REPO), 'DATA': str(DATA), 'RESULTS': str(RESULTS),
        'REFIT': str(REFIT), 'FIGURES': str(FIGURES), 'OUTPUT': str(OUTPUT),
    }


if __name__ == '__main__':
    import json
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(describe(), indent=1))
