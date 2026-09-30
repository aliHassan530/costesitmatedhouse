# Pakistan House Cost Estimator v2
pip install -r requirements.txt
uvicorn api:app --reload      ->  http://127.0.0.1:8000  (API docs: /docs)

- market_data.py : aap ka real 2021-2026 data + ASSUMED rates + city factors (yahan edit karein)
- engine.py      : rate/forecast/cost engine     - api.py : FastAPI (+ PDF quotation, CSV import)
- data/city_rates.csv : city-wise real rates (city,item,year,low,high). Dashboard se import ya file edit.
CSV wali city/item/year ke liye city factor ignore hota hai; agle saalon ka forecast us city ke last rate se chalta hai.
# costesitmatedhouse
