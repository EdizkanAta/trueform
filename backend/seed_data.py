"""Seed data: exercise catalog (movement-pattern based, for environment swaps)
and recipe catalog. Exercises are enriched with wger media attribution at seed
time. Movement patterns let the plan swap barbell -> dumbbell -> bodyweight
within the same pattern + muscle group when the training environment changes.
"""
from __future__ import annotations

from typing import Dict, List

from db import db
from media_provider import get_media_provider

# equipment tiers: "gym", "minimal" (home w/ equipment), "none" (bodyweight)
EXERCISES: List[Dict] = [
    # horizontal push
    {"slug": "barbell-bench-press", "name": "Barbell Bench Press", "pattern": "horizontal_push",
     "muscle_groups": ["chest", "triceps", "shoulders"], "equipment": "gym", "difficulty": "intermediate",
     "sets": 4, "reps": "6-8", "rest_sec": 120, "contraindications": ["hypertension_valsalva"]},
    {"slug": "dumbbell-bench-press", "name": "Dumbbell Bench Press", "pattern": "horizontal_push",
     "muscle_groups": ["chest", "triceps", "shoulders"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 4, "reps": "8-10", "rest_sec": 90, "contraindications": []},
    {"slug": "push-up", "name": "Push-Up", "pattern": "horizontal_push",
     "muscle_groups": ["chest", "triceps", "shoulders"], "equipment": "none", "difficulty": "beginner",
     "sets": 3, "reps": "10-15", "rest_sec": 60, "contraindications": []},
    # vertical push
    {"slug": "overhead-press", "name": "Overhead Barbell Press", "pattern": "vertical_push",
     "muscle_groups": ["shoulders", "triceps"], "equipment": "gym", "difficulty": "intermediate",
     "sets": 3, "reps": "6-8", "rest_sec": 120, "contraindications": ["hypertension_valsalva"]},
    {"slug": "dumbbell-shoulder-press", "name": "Dumbbell Shoulder Press", "pattern": "vertical_push",
     "muscle_groups": ["shoulders", "triceps"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 3, "reps": "8-12", "rest_sec": 90, "contraindications": []},
    {"slug": "pike-push-up", "name": "Pike Push-Up", "pattern": "vertical_push",
     "muscle_groups": ["shoulders", "triceps"], "equipment": "none", "difficulty": "intermediate",
     "sets": 3, "reps": "8-12", "rest_sec": 60, "contraindications": []},
    # horizontal pull
    {"slug": "barbell-row", "name": "Barbell Row", "pattern": "horizontal_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "gym", "difficulty": "intermediate",
     "sets": 4, "reps": "8-10", "rest_sec": 90, "contraindications": []},
    {"slug": "dumbbell-row", "name": "One-Arm Dumbbell Row", "pattern": "horizontal_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 4, "reps": "10-12", "rest_sec": 75, "contraindications": []},
    {"slug": "inverted-row-band", "name": "Band / Table Inverted Row", "pattern": "horizontal_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "none", "difficulty": "beginner",
     "sets": 3, "reps": "10-15", "rest_sec": 60, "contraindications": []},
    # vertical pull
    {"slug": "lat-pulldown", "name": "Lat Pulldown", "pattern": "vertical_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 90, "contraindications": []},
    {"slug": "pull-up", "name": "Pull-Up", "pattern": "vertical_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "minimal", "difficulty": "advanced",
     "sets": 3, "reps": "5-8", "rest_sec": 120, "contraindications": []},
    {"slug": "band-lat-pulldown", "name": "Band Lat Pulldown", "pattern": "vertical_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "none", "difficulty": "beginner",
     "sets": 3, "reps": "12-15", "rest_sec": 60, "contraindications": []},
    # squat
    {"slug": "back-squat", "name": "Barbell Back Squat", "pattern": "squat",
     "muscle_groups": ["quads", "glutes"], "equipment": "gym", "difficulty": "intermediate",
     "sets": 4, "reps": "6-8", "rest_sec": 150, "contraindications": ["hypertension_valsalva"]},
    {"slug": "goblet-squat", "name": "Goblet Squat", "pattern": "squat",
     "muscle_groups": ["quads", "glutes"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 4, "reps": "10-12", "rest_sec": 90, "contraindications": []},
    {"slug": "bodyweight-squat", "name": "Bodyweight Squat", "pattern": "squat",
     "muscle_groups": ["quads", "glutes"], "equipment": "none", "difficulty": "beginner",
     "sets": 3, "reps": "15-20", "rest_sec": 60, "contraindications": []},
    # hinge
    {"slug": "romanian-deadlift", "name": "Romanian Deadlift", "pattern": "hinge",
     "muscle_groups": ["hamstrings", "glutes", "back"], "equipment": "gym", "difficulty": "intermediate",
     "sets": 3, "reps": "8-10", "rest_sec": 120, "contraindications": ["hypertension_valsalva"]},
    {"slug": "dumbbell-rdl", "name": "Dumbbell Romanian Deadlift", "pattern": "hinge",
     "muscle_groups": ["hamstrings", "glutes"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 90, "contraindications": []},
    {"slug": "glute-bridge", "name": "Glute Bridge", "pattern": "hinge",
     "muscle_groups": ["glutes", "hamstrings"], "equipment": "none", "difficulty": "beginner",
     "sets": 3, "reps": "15-20", "rest_sec": 45, "contraindications": []},
    # conditioning / core
    {"slug": "incline-walk", "name": "Incline Treadmill Walk", "pattern": "conditioning",
     "muscle_groups": ["cardio"], "equipment": "gym", "difficulty": "beginner",
     "sets": 1, "reps": "20-30 min", "rest_sec": 0, "contraindications": [],
     "cardio": {"pace": "Brisk · 5–6 km/h (3.5 mph)", "incline": "6–10% incline", "duration": "20–30 min", "intensity": "RPE 6/10 — can talk, not sing"}},
    {"slug": "brisk-walk", "name": "Brisk Outdoor Walk", "pattern": "conditioning",
     "muscle_groups": ["cardio"], "equipment": "none", "difficulty": "beginner",
     "sets": 1, "reps": "20-30 min", "rest_sec": 0, "contraindications": [],
     "cardio": {"pace": "Brisk · 5.5–6.5 km/h (4 mph)", "incline": "Flat / natural terrain", "duration": "20–30 min", "intensity": "RPE 6/10 — can talk, not sing"}},
    {"slug": "plank", "name": "Plank", "pattern": "core",
     "muscle_groups": ["core"], "equipment": "none", "difficulty": "beginner",
     "sets": 3, "reps": "30-45 sec", "rest_sec": 45, "contraindications": []},
    {"slug": "dead-bug", "name": "Dead Bug", "pattern": "core",
     "muscle_groups": ["core"], "equipment": "none", "difficulty": "beginner",
     "sets": 3, "reps": "10-12/side", "rest_sec": 45, "contraindications": []},

    # ---- expanded catalog (cable / kettlebell / machine / dumbbell) ----
    # Variants slot into existing patterns; isolations use pattern "accessory"
    # (catalog-only — mapped media, not auto-inserted into the weekly split).
    {"slug": "chest-press-machine", "name": "Chest Press Machine", "pattern": "horizontal_push",
     "muscle_groups": ["chest", "triceps", "shoulders"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "8-12", "rest_sec": 90, "contraindications": []},
    {"slug": "seated-row-machine", "name": "Seated Row Machine", "pattern": "horizontal_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 90, "contraindications": []},
    {"slug": "cable-seated-row", "name": "Cable Seated Row", "pattern": "horizontal_pull",
     "muscle_groups": ["back", "biceps"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 90, "contraindications": []},
    {"slug": "leg-press", "name": "Leg Press", "pattern": "squat",
     "muscle_groups": ["quads", "glutes"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 120, "contraindications": []},
    {"slug": "kettlebell-goblet-squat", "name": "Kettlebell Goblet Squat", "pattern": "squat",
     "muscle_groups": ["quads", "glutes"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 90, "contraindications": []},
    {"slug": "dumbbell-lunge", "name": "Dumbbell Lunge", "pattern": "squat",
     "muscle_groups": ["quads", "glutes"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 3, "reps": "10-12/side", "rest_sec": 90, "contraindications": []},
    {"slug": "kettlebell-swing", "name": "Kettlebell Swing", "pattern": "hinge",
     "muscle_groups": ["glutes", "hamstrings", "back"], "equipment": "minimal", "difficulty": "intermediate",
     "sets": 3, "reps": "12-15", "rest_sec": 75, "contraindications": []},
    {"slug": "kettlebell-deadlift", "name": "Kettlebell Deadlift", "pattern": "hinge",
     "muscle_groups": ["glutes", "hamstrings", "back"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 90, "contraindications": []},
    {"slug": "cable-chest-fly", "name": "Cable Chest Fly", "pattern": "accessory",
     "muscle_groups": ["chest"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "12-15", "rest_sec": 60, "contraindications": []},
    {"slug": "triceps-pushdown", "name": "Triceps Pushdown", "pattern": "accessory",
     "muscle_groups": ["triceps"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "12-15", "rest_sec": 60, "contraindications": []},
    {"slug": "face-pull", "name": "Face Pull", "pattern": "accessory",
     "muscle_groups": ["shoulders", "back"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "12-15", "rest_sec": 60, "contraindications": []},
    {"slug": "leg-curl", "name": "Leg Curl", "pattern": "accessory",
     "muscle_groups": ["hamstrings"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "12-15", "rest_sec": 60, "contraindications": []},
    {"slug": "leg-extension", "name": "Leg Extension", "pattern": "accessory",
     "muscle_groups": ["quads"], "equipment": "gym", "difficulty": "beginner",
     "sets": 3, "reps": "12-15", "rest_sec": 60, "contraindications": []},
    {"slug": "dumbbell-lateral-raise", "name": "Dumbbell Lateral Raise", "pattern": "accessory",
     "muscle_groups": ["shoulders"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 3, "reps": "12-15", "rest_sec": 60, "contraindications": []},
    {"slug": "dumbbell-biceps-curl", "name": "Dumbbell Biceps Curl", "pattern": "accessory",
     "muscle_groups": ["biceps"], "equipment": "minimal", "difficulty": "beginner",
     "sets": 3, "reps": "10-12", "rest_sec": 60, "contraindications": []},
]

PATTERN_CUES = {
    "horizontal_push": ["Brace your core, shoulder blades back and down", "Lower under control to mid-chest", "Press without flaring elbows past 45°"],
    "vertical_push": ["Ribs down, glutes tight", "Press straight overhead, biceps by your ears", "Don't overarch the lower back"],
    "horizontal_pull": ["Pull your elbow toward your hip, not up", "Squeeze the shoulder blade at the top", "Keep your neck long and relaxed"],
    "vertical_pull": ["Start from a full hang/stretch", "Drive your elbows down to your ribs", "Avoid swinging or kipping"],
    "squat": ["Feet shoulder-width, toes slightly out", "Sit down and back, knees track over toes", "Drive through mid-foot to stand"],
    "hinge": ["Soft knees, push your hips back", "Keep the weight close to your legs", "Flat back — hinge, don't round"],
    "conditioning": ["Keep an easy, conversational pace", "Relaxed shoulders, steady breathing", "Land mid-foot with light steps"],
    "core": ["Breathe steadily, don't hold your breath", "Keep the lower back neutral", "Move slowly with control"],
    "accessory": ["Control the weight both ways — no swinging", "Full range, squeeze the target muscle", "Keep the rest of your body still"],
}

RECIPES: List[Dict] = [
    {"slug": "greek-yogurt-bowl", "name": "Greek Yogurt & Berry Bowl", "kcal": 320,
     "macros": {"protein_g": 28, "carbs_g": 34, "fat_g": 8}, "meal_type": "breakfast",
     "tags": ["vegetarian", "diabetic-friendly", "high-protein"],
     "ingredients": ["200g Greek yogurt", "80g mixed berries", "20g oats", "1 tsp honey"],
     "steps": ["Combine yogurt and oats.", "Top with berries and honey."]},
    {"slug": "veggie-omelette", "name": "Three-Egg Veggie Omelette", "kcal": 340,
     "macros": {"protein_g": 26, "carbs_g": 8, "fat_g": 22}, "meal_type": "breakfast",
     "tags": ["vegetarian", "low-sodium", "diabetic-friendly"],
     "ingredients": ["3 eggs", "Spinach", "Tomato", "Onion", "1 tsp olive oil"],
     "steps": ["Whisk eggs.", "Saute veg, add eggs, fold and cook."]},
    {"slug": "oat-protein-porridge", "name": "Oat Protein Porridge", "kcal": 380,
     "macros": {"protein_g": 30, "carbs_g": 48, "fat_g": 8}, "meal_type": "breakfast",
     "tags": ["vegetarian", "high-protein"],
     "ingredients": ["60g oats", "1 scoop whey", "250ml milk", "Cinnamon"],
     "steps": ["Cook oats with milk.", "Stir in whey and cinnamon off heat."]},
    {"slug": "chicken-quinoa-bowl", "name": "Chicken & Quinoa Bowl", "kcal": 520,
     "macros": {"protein_g": 45, "carbs_g": 48, "fat_g": 14}, "meal_type": "lunch",
     "tags": ["halal", "high-protein", "diabetic-friendly"],
     "ingredients": ["150g chicken breast", "80g quinoa", "Mixed greens", "Olive oil", "Lemon"],
     "steps": ["Grill chicken.", "Cook quinoa.", "Assemble with greens and dressing."]},
    {"slug": "lentil-veg-curry", "name": "Lentil & Vegetable Curry", "kcal": 460,
     "macros": {"protein_g": 24, "carbs_g": 62, "fat_g": 12}, "meal_type": "lunch",
     "tags": ["vegetarian", "halal", "low-sodium"],
     "ingredients": ["120g red lentils", "Mixed vegetables", "Tomato", "Spices", "1 tsp oil"],
     "steps": ["Simmer lentils with spices.", "Add vegetables, cook until tender."]},
    {"slug": "salmon-sweet-potato", "name": "Baked Salmon & Sweet Potato", "kcal": 540,
     "macros": {"protein_g": 40, "carbs_g": 40, "fat_g": 22}, "meal_type": "dinner",
     "tags": ["low-sodium", "high-protein", "heart-healthy"],
     "ingredients": ["160g salmon", "200g sweet potato", "Broccoli", "Olive oil"],
     "steps": ["Bake salmon and sweet potato.", "Steam broccoli."]},
    {"slug": "turkey-stir-fry", "name": "Turkey & Veg Stir-Fry", "kcal": 480,
     "macros": {"protein_g": 42, "carbs_g": 38, "fat_g": 14}, "meal_type": "dinner",
     "tags": ["halal", "high-protein", "diabetic-friendly"],
     "ingredients": ["150g turkey mince", "Mixed stir-fry veg", "60g brown rice", "Low-sodium soy"],
     "steps": ["Brown turkey.", "Add veg and sauce.", "Serve over rice."]},
    {"slug": "tofu-veg-bowl", "name": "Tofu & Vegetable Bowl", "kcal": 450,
     "macros": {"protein_g": 28, "carbs_g": 44, "fat_g": 16}, "meal_type": "dinner",
     "tags": ["vegetarian", "vegan", "low-sodium"],
     "ingredients": ["200g firm tofu", "Mixed vegetables", "60g rice", "Sesame oil"],
     "steps": ["Pan-fry tofu.", "Add veg.", "Serve over rice."]},
    {"slug": "cottage-cheese-snack", "name": "Cottage Cheese & Almonds", "kcal": 220,
     "macros": {"protein_g": 22, "carbs_g": 8, "fat_g": 11}, "meal_type": "snack",
     "tags": ["vegetarian", "high-protein", "diabetic-friendly"],
     "ingredients": ["150g cottage cheese", "15g almonds"],
     "steps": ["Combine and serve."]},
    {"slug": "apple-peanut-butter", "name": "Apple & Peanut Butter", "kcal": 210,
     "macros": {"protein_g": 7, "carbs_g": 26, "fat_g": 10}, "meal_type": "snack",
     "tags": ["vegetarian", "vegan"],
     "ingredients": ["1 apple", "1 tbsp peanut butter"],
     "steps": ["Slice apple and serve with peanut butter."]},
    {"slug": "protein-shake-banana", "name": "Protein Shake & Banana", "kcal": 260,
     "macros": {"protein_g": 27, "carbs_g": 30, "fat_g": 4}, "meal_type": "snack",
     "tags": ["vegetarian", "high-protein"],
     "ingredients": ["1 scoop whey", "1 banana", "250ml milk"],
     "steps": ["Blend and serve."]},
    {"slug": "hummus-veg-sticks", "name": "Hummus & Veg Sticks", "kcal": 180,
     "macros": {"protein_g": 7, "carbs_g": 20, "fat_g": 9}, "meal_type": "snack",
     "tags": ["vegetarian", "vegan", "halal", "low-sodium"],
     "ingredients": ["60g hummus", "Carrot & cucumber sticks"],
     "steps": ["Serve veg with hummus."]},
]


async def seed_if_empty() -> None:
    count = await db.exercises.count_documents({})
    if count == 0:
        provider = get_media_provider()
        docs = []
        for ex in EXERCISES:
            media = provider.enrich(ex["name"])
            docs.append({**ex, "media": media, "media_provider": provider.name,
                         "form_cues": PATTERN_CUES.get(ex["pattern"], []),
                         "poster_image_url": media.get("demo_url")})
        if docs:
            await db.exercises.insert_many(docs)

    if await db.recipes.count_documents({}) == 0:
        await db.recipes.insert_many([{**r} for r in RECIPES])

    await backfill_exercise_cues()


async def backfill_exercise_cues() -> None:
    """Add form_cues + poster_image_url to any exercise docs missing them."""
    async for ex in db.exercises.find({"form_cues": {"$exists": False}}):
        await db.exercises.update_one({"slug": ex["slug"]}, {"$set": {
            "form_cues": PATTERN_CUES.get(ex.get("pattern"), []),
            "poster_image_url": (ex.get("media") or {}).get("demo_url"),
        }})
