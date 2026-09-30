"""api.py - Chalao: uvicorn api:app --reload   ->  http://127.0.0.1:8000  (docs: /docs)"""
from pathlib import Path
from typing import Literal

from io import BytesIO

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from engine import CITY, CSV_PATH, LEVELS, STAGES, catalog, estimate, load_csv
from market_data import FIRST, MAX_YEAR

app = FastAPI(title="Pakistan House Cost Estimator", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Sel(BaseModel):
    enabled: bool = True
    variant: str | None = None


class Req(BaseModel):
    city: Literal[tuple(CITY)] = "Lahore"
    marla: float = Field(5, ge=1, le=40)
    floors: int = Field(1, ge=1, le=3)
    year: int = Field(2026, ge=FIRST, le=MAX_YEAR)
    stage: Literal[tuple(STAGES)] = "finished"
    level: Literal[tuple(LEVELS)] = "market"
    beds: int = Field(3, ge=0, le=20)
    baths: int = Field(3, ge=0, le=20)
    kitchens: int = Field(1, ge=0, le=6)
    items: dict[str, Sel] = {}


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(Path(__file__).parent / "dashboard.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/catalog")
def get_catalog():
    return catalog()


@app.post("/api/estimate")
def post_estimate(req: Req):
    d = req.model_dump()
    d["items"] = {k: v for k, v in d["items"].items()}
    return estimate(d)


TEMPLATE = """# city,item,year,low,high  (item: cement, bricks[per 1000], steel, crush_s, crush_m, labour, alu, upvc, elec, plumb, ceramic, porcelain, cab_std, cab_pre, cab_lux, sand, plaster, paint, door, wall, gate, foundation)
city,item,year,low,high
Karachi,cement,2026,1650,1780
Karachi,steel,2026,255,292
Multan,bricks,2026,11500,14000
"""


@app.get("/api/csv-template", response_class=PlainTextResponse)
def csv_template():
    return PlainTextResponse(TEMPLATE, headers={"Content-Disposition": "attachment; filename=city_rates.csv"})


@app.post("/api/import-csv")
async def import_csv(request: Request):
    text = (await request.body()).decode("utf-8-sig")
    n = load_csv(text)
    if n == 0:
        raise HTTPException(422, "CSV mein koi valid row nahi mili (columns: city,item,year,low,high)")
    CSV_PATH.parent.mkdir(exist_ok=True)
    CSV_PATH.write_text(text, encoding="utf-8")
    return {"rows": n}


def pkr(n):
    return f"PKR {round(n):,}"


@app.post("/api/quote.pdf")
def quote_pdf(req: Req):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from datetime import date
    d = estimate(req.model_dump())
    st = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    kind = "Forecast" if d["is_forecast"] else "Estimate"
    s = [Paragraph("House Construction Cost Quotation", st["Title"]),
         Paragraph(f"{req.city} | {req.marla:g} marla | {req.floors} floor(s) | {req.stage.replace('semi','semi-finished')} | "
                   f"{req.beds} bed, {req.baths} bath, {req.kitchens} kitchen | rates {req.year} | {date.today():%d %b %Y}", st["Normal"]),
         Spacer(1, 10),
         Paragraph(f"<b>{kind}: {pkr(d['total'])}</b> (likely range {pkr(d['low'])} - {pkr(d['high'])}) | "
                   f"{pkr(d['per_sqft'])} per sq ft on {d['covered_sqft']:,.0f} sq ft", st["Heading3"]), Spacer(1, 8)]
    rows = [["Item", "Qty", "Unit rate", "Cost"]]
    for l in sorted(d["lines"], key=lambda x: -x["cost"]):
        name = l["en"] + (f" ({l['variant']})" if l["variant"] else "") + (f" [{int(l['scope']*100)}%]" if l["scope"] < 1 else "") + (" *" if l["assumed"] else "")
        rows.append([name, f"{l['qty']:,.1f} {l['unit']}", f"{l['unit_rate']:,.0f}", pkr(l["cost"])])
    rows.append(["TOTAL", "", "", pkr(d["total"])])
    t = Table(rows, colWidths=[200, 130, 70, 110], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                           ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"), ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey)]))
    s += [t, Spacer(1, 10), Paragraph("* = assumed rate (not from market survey). Semi-finished [%] = partial scope. "
          "This is an approximate estimate based on market rate ranges; final cost depends on contractor quotes, design and site conditions.", st["Italic"])]
    doc.build(s)
    return Response(buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=house_quotation.pdf"})
