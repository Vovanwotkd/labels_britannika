"""
Diagnostic script to check TSPL rendering and sizes
"""

import sys
sys.path.insert(0, '/app')

from app.services.printer.tspl_renderer import TSPLRenderer
from app.core.database import SessionLocal, dishes_db
from app.models import Template, PrintJob
import json

print("=" * 80)
print("TSPL SIZE DIAGNOSTIC")
print("=" * 80)

# 1. Check if new code is loaded
print("\n1. Checking code version...")
renderer_test = TSPLRenderer({"paper_width_mm": 58})
if hasattr(renderer_test, '_render_with_elements'):
    print("   ✅ NEW CODE loaded (_render_with_elements exists)")
    print(f"   ✅ bitmap_width default: {renderer_test.bitmap_width}")
else:
    print("   ❌ OLD CODE loaded (missing _render_with_elements)")

# 2. Get template from DB
print("\n2. Checking template...")
db = SessionLocal()
template = db.query(Template).filter(Template.is_default == True).first()

if not template:
    print("   ❌ No default template found!")
    sys.exit(1)

print(f"   Template: {template.name} (ID: {template.id})")
print(f"   Has 'elements' key: {'elements' in template.config}")
print(f"   Has 'bitmap_width' key: {'bitmap_width' in template.config}")

if 'elements' in template.config:
    print(f"   Elements count: {len(template.config['elements'])}")
if 'bitmap_width' in template.config:
    print(f"   bitmap_width setting: {template.config['bitmap_width']}")

# 3. Generate test TSPL
print("\n3. Generating test TSPL...")

# Get a real dish
dish = dishes_db.get_dish_by_rk_code("2538")  # Лепешка с говядиной
if not dish:
    # Try to get any dish
    all_dishes = dishes_db.get_all_dishes()
    if all_dishes:
        dish = all_dishes[0]
    else:
        print("   ❌ No dishes in database!")
        sys.exit(1)

dish_data = {
    "name": dish["name"],
    "rk_code": dish["rkeeper_code"],
    "weight_g": dish["weight_g"],
    "calories": dish["calories"],
    "protein": dish["protein"],
    "fat": dish["fat"],
    "carbs": dish["carbs"],
    "ingredients": dish.get("ingredients", []),
    "label_type": "MAIN",
}

renderer = TSPLRenderer(template.config)
tspl = renderer.render(dish_data)

print(f"   Dish: {dish_data['name']}")
print(f"   TSPL size: {len(tspl)} bytes ({len(tspl)/1024:.2f} KB)")
print(f"   Rendering method: {'elements' if renderer.use_elements else 'legacy'}")

# 4. Show first 500 chars of TSPL
print("\n4. TSPL preview (first 500 chars):")
print("-" * 80)
print(tspl[:500])
print("-" * 80)

# 5. Count BITMAP commands
bitmap_count = tspl.count("BITMAP")
print(f"\n5. BITMAP commands count: {bitmap_count}")

# 6. Check recent failed jobs
print("\n6. Checking recent failed jobs...")
failed_jobs = db.query(PrintJob)\
    .filter(PrintJob.status == "FAILED")\
    .order_by(PrintJob.id.desc())\
    .limit(3)\
    .all()

if failed_jobs:
    for job in failed_jobs:
        print(f"\n   Job #{job.id}:")
        print(f"     Status: {job.status}")
        print(f"     Size: {len(job.tspl_data)} bytes ({len(job.tspl_data)/1024:.2f} KB)")
        print(f"     Error: {job.error_message}")
        print(f"     Retry count: {job.retry_count}/{job.max_retries}")

        # Show first 200 chars of TSPL
        print(f"     TSPL preview: {job.tspl_data[:200]}...")
else:
    print("   No failed jobs found")

db.close()

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

# 7. Size comparison
print("\nEXPECTED vs ACTUAL:")
print(f"  Expected: ~5,000 bytes (5 KB) with optimizations")
print(f"  Actual (test): {len(tspl)} bytes ({len(tspl)/1024:.2f} KB)")

if len(tspl) > 10000:
    print("\n⚠️  WARNING: TSPL size is too large!")
    print("   Possible causes:")
    print("   - Old code still running (Docker cache)")
    print("   - Template config has no optimizations")
    print("   - bitmap_width not set (should be 280)")
elif len(tspl) > 6000:
    print("\n⚠️  Size is better but still high")
    print("   Consider further optimization")
else:
    print("\n✅ Size looks good!")
