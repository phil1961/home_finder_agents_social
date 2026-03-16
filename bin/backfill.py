# v20260309-1
from app.services.place_geocoder import backfill_place_names
from app import create_app
app = create_app()
with app.app_context():
    n = backfill_place_names(app)
    print(f"Updated {n} listings")