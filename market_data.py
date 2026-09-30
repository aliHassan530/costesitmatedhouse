"""market_data.py - Aap ka REAL data (2021-2026, har entry = (low, high) PKR).
Naya saal aaye to har list mein ek tuple append karo aur LAST badlo."""
FIRST, LAST, MAX_YEAR = 2021, 2026, 2031
MAX_G = 0.15      # forecast growth ki hadd (15%/saal)
WIDEN = 0.03      # har forecast saal par range 3% wide

DATA = {
 "cement":  [(600,740),(850,1050),(1100,1250),(1200,1450),(1350,1550),(1560,1670)],          # per bag
 "bricks":  [(6500,7500),(8000,9500),(10000,11500),(11500,13000),(12000,14000),(12000,15000)],  # per 1000
 "crush_s": [(65,75),(80,95),(95,115),(110,130),(125,150),(130,190)],                         # Sargodha /cft
 "crush_m": [(85,95),(105,125),(130,145),(140,165),(165,190),(170,330)],                      # Margalla /cft
 "steel":   [(140,160),(195,235),(260,290),(245,270),(260,285),(250,286)],                    # per kg
 "labour":  [(250,350),(350,450),(450,580),(550,680),(650,750),(700,990)],                    # grey /sqft
 "alu":     [(750,1000),(950,1300),(1300,1800),(1500,2200),(1800,2800),(2000,3500)],          # /sqft
 "upvc":    [(850,1100),(1100,1400),(1350,1900),(1500,2400),(1600,2800),(1800,3500)],
 "elec":    [(180000,250000),(250000,350000),(350000,480000),(450000,600000),(550000,700000),(600000,900000)],
 "plumb":   [(185000,250000),(250000,350000),(340000,480000),(450000,600000),(550000,750000),(600000,900000)],
 "ceramic": [(60,110),(80,140),(100,180),(110,210),(115,230),(120,250)],
 "porcelain":[(90,160),(120,220),(150,290),(160,320),(170,340),(130,350)],
 "cab_std": [(900,1200),(1200,1600),(1600,2100),(1900,2400),(2100,2600),(2300,2800)],
 "cab_pre": [(1400,1800),(1900,2400),(2500,3200),(3000,3800),(3300,4200),(3500,4500)],
 "cab_lux": [(2500,3500),(3200,4500),(4500,6000),(5500,7200),(6200,8000),(6800,9000)],
}

# ASSUMED: aap ke data mein nahi tha. Sirf 2026 ki (low, high) + kis series ke index se pichlay/agle saal nikalne hain.
# Real rate milne par yahan number badlo.
ASSUMED = {
 "sand":       (80, 100, "crush_s"),      # per cft
 "foundation": (30000, 40000, "mat"),     # per marla
 "wall":       (2600, 3400, "mat"),       # per running ft
 "gate":       (70000, 120000, "mat"),    # ek gate
 "plaster":    (140, 230, "labour"),      # per sqft covered
 "paint":      (110, 280, "mat"),         # per sqft covered
 "tile_fix":   (80, 120, "labour"),       # tile lagai per sqft
 "door":       (30000, 100000, "cab_std"),# lakri ka darwaza + chokhat (per door)
}

# City factors (material, labour) - Lahore = 1. ASSUMED, city-wise real rates milne par badlo.
CITY = {"Lahore":(1,1), "Karachi":(1.06,1.10), "Islamabad":(1.08,1.15),
        "Faisalabad":(0.97,0.92), "Multan":(0.96,0.88), "Sahiwal":(0.94,0.85)}

# Reference ghar jis ka electrical/plumbing budget aap ke table mein hai (ASSUMED: 5 marla, 2 manzil, 4 bathroom)
REF_AREA, REF_BATHS = 2250, 4

NOTES = [
 "Electrical 2026 ki upper limit table mein kati hui thi; 900,000 (labour 360k + material 540k) maani gayi hai.",
 "Porcelain tile 2026 low (130) 2025 low (170) se kam hai - check karein ke typo to nahi.",
 "Margalla crush 2026 high (330) trend se bohot upar hai - outlier ho sakta hai.",
 "Sand, foundation, wall, gate, plaster, paint, tile fixing, lakri ke darwaze aur city factors ASSUMED hain (dashboard mein 'Assumed' badge).",
]
