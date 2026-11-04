#!/usr/bin/env python
"""Create a self-contained HTML comparison report with a five-axis radar chart.

Example:
    .venv/bin/python scripts/eval_report.py evals/runs/BASE.jsonl \
        --compare evals/runs/CANDIDATE.jsonl

Human ratings are read from the corresponding JSONL files in evals/labels/;
pass --labels and --compare-labels to override those paths.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AXES = {
    "factuality": "Factualidad",
    "relevance": "Respuesta",
    "missing_information": "Datos ausentes",
    "language_tone": "Idioma y tono",
    "guardrails": "Guardrails",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on {path}:{line_number}: {exc}") from exc
    return records


def load_run(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    records = read_jsonl(path)
    header = next((row for row in records if row.get("record_type") == "run"), None)
    if header is None:
        raise ValueError(f"No run header found in {path}")
    cases = {row["id"]: row for row in records if row.get("record_type") == "case"}
    return header, cases


def load_labels(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    return {row["id"]: row for row in read_jsonl(path) if "id" in row}


def mean_axis(labels: dict[str, dict[str, Any]], axis: str) -> float | None:
    values = [
        row.get("scores", {}).get(axis)
        for row in labels.values()
        if row.get("scores", {}).get(axis) in (1, 2, 3)
    ]
    return sum(values) / len(values) if values else None


def label_path_for(header: dict[str, Any]) -> Path:
    return ROOT / "evals" / "labels" / f"{header['run_id']}.jsonl"


def _escape(value: Any) -> str:
    return html.escape(str(value or ""))


def _score_summary(labels: dict[str, dict[str, Any]]) -> str:
    values = [row["overall"] for row in labels.values() if row.get("overall") in (1, 2, 3)]
    return f"{sum(values) / len(values):.2f}" if values else "Sin etiquetas"


def _approval_message(
    baseline_labels: dict[str, dict[str, Any]],
    candidate_labels: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    shared_ids = baseline_labels.keys() & candidate_labels.keys()
    if not shared_ids:
        return "Pendiente", "Faltan etiquetas humanas comparables para ambos runs."

    new_fabrications = [
        case_id
        for case_id in shared_ids
        if candidate_labels[case_id].get("blocking_fabrication") is True
        and baseline_labels[case_id].get("blocking_fabrication") is not True
    ]
    regressions = []
    for axis, title in AXES.items():
        base = mean_axis({key: baseline_labels[key] for key in shared_ids}, axis)
        candidate = mean_axis({key: candidate_labels[key] for key in shared_ids}, axis)
        if base is not None and candidate is not None and candidate < base - 0.25:
            regressions.append(f"{title} ({base:.2f} → {candidate:.2f})")
    if new_fabrications or regressions:
        reasons = []
        if new_fabrications:
            reasons.append("fabricaciones nuevas: " + ", ".join(sorted(new_fabrications)))
        if regressions:
            reasons.append("regresión >0,25: " + ", ".join(regressions))
        return "No pasa", "; ".join(reasons)
    if any(mean_axis(candidate_labels, axis) is None for axis in AXES):
        return "Pendiente", "Faltan puntuaciones por eje para aplicar el umbral completo."
    return "Pasa el umbral", "Sin fabricaciones nuevas y ningún eje baja más de 0,25."


def _case_score(labels: dict[str, dict[str, Any]], case_id: str) -> str:
    row = labels.get(case_id, {})
    overall = row.get("overall")
    return str(overall) if overall in (1, 2, 3) else "—"


def _render_case_rows(
    baseline: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    base_labels: dict[str, dict[str, Any]],
    candidate_labels: dict[str, dict[str, Any]],
) -> str:
    ids = list(dict.fromkeys([*baseline.keys(), *candidate.keys()]))
    rows = []
    for case_id in ids:
        left, right = baseline.get(case_id, {}), candidate.get(case_id, {})
        question = left.get("question") or right.get("question") or ""
        rows.append(
            "<tr>"
            f"<th>{_escape(case_id)}<br><small>{_escape(left.get('category') or right.get('category'))}</small></th>"
            f"<td class='question'>{_escape(question)}</td>"
            f"<td>{_case_score(base_labels, case_id)}</td>"
            f"<td class='answer'>{_escape(left.get('answer') or left.get('error') or '—')}</td>"
            f"<td>{_case_score(candidate_labels, case_id)}</td>"
            f"<td class='answer'>{_escape(right.get('answer') or right.get('error') or '—')}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_report(
    baseline_path: Path,
    compare_path: Path | None,
    baseline_labels_path: Path | None,
    compare_labels_path: Path | None,
    output_path: Path,
) -> None:
    base_header, baseline = load_run(baseline_path)
    base_labels = load_labels(baseline_labels_path or label_path_for(base_header))
    compare_header, candidate = ({}, {})
    candidate_labels: dict[str, dict[str, Any]] = {}
    if compare_path:
        compare_header, candidate = load_run(compare_path)
        candidate_labels = load_labels(compare_labels_path or label_path_for(compare_header))

    series = [{"name": "Línea base", "values": [mean_axis(base_labels, axis) for axis in AXES]}]
    if compare_path:
        series.append({"name": "Experimento", "values": [mean_axis(candidate_labels, axis) for axis in AXES]})
    series_json = json.dumps(series, ensure_ascii=False).replace("<", "\\u003c")
    axis_json = json.dumps(list(AXES.values()), ensure_ascii=False).replace("<", "\\u003c")
    rows = _render_case_rows(baseline, candidate, base_labels, candidate_labels)
    status, details = _approval_message(base_labels, candidate_labels) if compare_path else (
        "Pendiente", "La línea base está lista; puntúa cada caso para dibujar el radar."
    )
    candidate_title = _escape(compare_header.get("run_id", "Experimento")) if compare_path else "—"
    candidate_score = _score_summary(candidate_labels) if compare_path else "—"
    report_title = "Comparación EDD" if compare_path else "Línea base EDD"

    document = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{report_title}</title>
<style>
:root{{color-scheme:light;--ink:#18212f;--muted:#657286;--line:#d9e0e8;--paper:#f4f6f8;--blue:#1769aa;--orange:#cb6525}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1400px;margin:0 auto;padding:32px 22px}}h1{{margin:0;font-size:clamp(1.8rem,4vw,2.8rem)}}h2{{margin:0 0 14px;font-size:1.2rem}}
.muted{{color:var(--muted)}}.top{{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:24px}}
.grid{{display:grid;grid-template-columns:minmax(300px,1fr) minmax(280px,0.8fr);gap:18px}}.card{{background:white;border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 4px 18px #18212f0a}}
.summary{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}}.metric{{padding:12px;background:#f7f9fb;border-radius:10px}}.metric b{{display:block;font-size:1.2rem}}
#radar{{width:min(100%,520px);height:auto;display:block;margin:0 auto}}.legend{{display:flex;gap:18px;justify-content:center;flex-wrap:wrap}}.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;background:var(--blue)}}.dot.orange{{background:var(--orange)}}
.decision{{border-left:4px solid var(--blue);padding:12px 14px;background:#f3f8fc;border-radius:5px}}.decision.fail{{border-color:#b92e32;background:#fff4f3}}.decision.pending{{border-color:#c28b15;background:#fff9e8}}
.table-wrap{{overflow:auto;margin-top:18px}}table{{width:100%;border-collapse:collapse;background:white;font-size:13px}}th,td{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid var(--line);min-width:90px}}thead th{{position:sticky;top:0;background:#edf1f5;z-index:1}}td.question{{min-width:210px}}td.answer{{min-width:280px;white-space:pre-wrap;max-width:430px}}small{{color:var(--muted);font-weight:400}}
.foot{{margin-top:20px;font-size:12px;color:var(--muted)}}@media(max-width:850px){{.grid{{grid-template-columns:1fr}}.top{{align-items:start;flex-direction:column}}.summary{{grid-template-columns:1fr}}}}
</style></head><body><main>
<div class="top"><div><p class="muted">Evaluation-driven development · revisión humana</p><h1>{report_title}</h1></div><p class="muted">Escala 1–3 · 3 positivo</p></div>
<div class="grid"><section class="card"><h2>Radar por eje</h2><svg id="radar" viewBox="0 0 560 500" role="img" aria-label="Comparación de puntuaciones medias por eje"></svg><div class="legend" id="legend"></div><p class="muted" id="radar-note"></p></section>
<section class="card"><h2>Resumen</h2><div class="summary"><div class="metric"><span class="muted">Línea base</span><b>{_escape(base_header.get('run_id', '—'))}</b><span>Media global: {_escape(_score_summary(base_labels))}</span></div><div class="metric"><span class="muted">Experimento</span><b>{candidate_title}</b><span>Media global: {candidate_score}</span></div><div class="metric"><span class="muted">Casos</span><b>{len(baseline)} / {len(candidate) if compare_path else '—'}</b><span>base / experimento</span></div></div>
<div class="decision {'fail' if status == 'No pasa' else 'pending' if status == 'Pendiente' else ''}"><strong>{_escape(status)}</strong><br>{_escape(details)}</div>
<p class="foot">Umbral acordado: cero fabricaciones nuevas y ningún eje puede empeorar su media más de 0,25. Los costes no se estiman si el proveedor no devuelve ese dato; los tokens disponibles sí se guardan en cada run.</p></section></div>
<section class="card table-wrap"><h2>Respuestas caso a caso</h2><table><thead><tr><th>ID / categoría</th><th>Pregunta</th><th>Nota base</th><th>Respuesta base</th><th>Nota exp.</th><th>Respuesta exp.</th></tr></thead><tbody>{rows}</tbody></table></section>
<p class="foot">Runs: {_escape(baseline_path)}{(' · ' + _escape(compare_path)) if compare_path else ''}. Este HTML es autocontenido y no carga recursos externos.</p>
</main><script>
const AXES={axis_json};const SERIES={series_json};const svg=document.getElementById('radar');const legend=document.getElementById('legend');const note=document.getElementById('radar-note');
const colors=['#1769aa','#cb6525'];const cx=280,cy=225,maxR=160,n=AXES.length;const ns='http://www.w3.org/2000/svg';
function el(tag,attrs={{}}){{const node=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))node.setAttribute(k,v);svg.appendChild(node);return node}}
for(let level=1;level<=3;level++){{const r=maxR*level/3;const pts=AXES.map((_,i)=>{{const a=-Math.PI/2+i*2*Math.PI/n;return `${{cx+r*Math.cos(a)}},${{cy+r*Math.sin(a)}}`}}).join(' ');el('polygon',{{points:pts,fill:'none',stroke:'#d9e0e8','stroke-width':'1'}});const t=el('text',{{x:cx+5,y:cy-r+14,fill:'#657286','font-size':'11'}});t.textContent=String(level)}}
AXES.forEach((axis,i)=>{{const a=-Math.PI/2+i*2*Math.PI/n;const x=cx+(maxR+35)*Math.cos(a),y=cy+(maxR+35)*Math.sin(a);el('line',{{x1:cx,y1:cy,x2:cx+maxR*Math.cos(a),y2:cy+maxR*Math.sin(a),stroke:'#d9e0e8'}});const t=el('text',{{x,y,fill:'#18212f','font-size':'12','text-anchor':Math.abs(Math.cos(a))<0.2?'middle':Math.cos(a)>0?'start':'end','dominant-baseline':'middle'}});t.textContent=axis}});
let plotted=0;SERIES.forEach((series,s)=>{{const complete=series.values.length===n&&series.values.every(v=>typeof v==='number');if(!complete)return;const pts=series.values.map((v,i)=>{{const a=-Math.PI/2+i*2*Math.PI/n,r=maxR*v/3;return `${{cx+r*Math.cos(a)}},${{cy+r*Math.sin(a)}}`}}).join(' ');el('polygon',{{points:pts,fill:colors[s], 'fill-opacity':'0.13',stroke:colors[s],'stroke-width':'3'}});series.values.forEach((v,i)=>{{const a=-Math.PI/2+i*2*Math.PI/n,r=maxR*v/3;el('circle',{{cx:cx+r*Math.cos(a),cy:cy+r*Math.sin(a),r:4,fill:colors[s]}})}});const item=document.createElement('span');item.innerHTML=`<i class="dot ${{s?'orange':''}}"></i>${{series.name}}`;legend.appendChild(item);plotted++}});
if(!plotted)note.textContent='Añade puntuaciones humanas (1–3) en evals/labels/*.jsonl y vuelve a generar el informe para ver el radar.';
</script></body></html>"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    print(f"Wrote {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="baseline JSONL run")
    parser.add_argument("--compare", type=Path, help="candidate JSONL run")
    parser.add_argument("--labels", type=Path, help="baseline human labels JSONL")
    parser.add_argument("--compare-labels", type=Path, help="candidate human labels JSONL")
    parser.add_argument("--output", type=Path, help="HTML output path")
    args = parser.parse_args()
    default_name = "baseline.html" if not args.compare else "comparison.html"
    output = args.output or ROOT / "evals" / "reports" / default_name
    try:
        build_report(args.baseline, args.compare, args.labels, args.compare_labels, output)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
