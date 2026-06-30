"""
Generate sample NGO survey data similar to Somrita's work at Development Alternatives.
Run this once to create sample_data/survey_data.csv
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)

regions = ["Delhi", "Ghaziabad", "Noida", "Faridabad", "Gurugram"]
surveyors = ["Priya S.", "Arjun K.", "Meena R.", "Ravi T.", "Sonal B."]
water_sources = ["Tap", "Borewell", "Hand Pump", "River", "Tanker"]
sanitation_types = ["Flush Toilet", "Pit Latrine", "Open Defecation", "Community Toilet"]
statuses = ["Complete", "Partial", "Dropout"]

start_date = date(2024, 6, 1)

rows = []
for i in range(1, 301):
    survey_date = start_date + timedelta(days=random.randint(0, 365))
    region = random.choice(regions)
    surveyor = random.choice(surveyors)
    water_source = random.choice(water_sources)
    sanitation = random.choice(sanitation_types)
    # Make dropouts slightly more common in certain regions
    if region in ["Faridabad", "Ghaziabad"]:
        status = random.choices(statuses, weights=[55, 25, 20])[0]
    else:
        status = random.choices(statuses, weights=[70, 20, 10])[0]

    household_size = random.randint(2, 8)
    monthly_income = random.randint(8000, 60000) // 1000 * 1000
    distance_to_water = round(random.uniform(0.1, 5.0), 1)  # km
    satisfaction_score = random.randint(1, 5)

    rows.append({
        "survey_id": f"SRV{i:04d}",
        "survey_date": survey_date.isoformat(),
        "region": region,
        "surveyor": surveyor,
        "household_size": household_size,
        "monthly_income_inr": monthly_income,
        "primary_water_source": water_source,
        "sanitation_type": sanitation,
        "distance_to_water_km": distance_to_water,
        "satisfaction_score": satisfaction_score,
        "survey_status": status,
        "toilet_access": random.choice(["Yes", "No"]),
        "handwash_facility": random.choice(["Yes", "No"]),
    })

with open("survey_data.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} survey records → survey_data.csv")
