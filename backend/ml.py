from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORIES = {
    'wedding': ['Venue', 'Catering', 'Decor', 'Photography', 'Entertainment', 'Beauty & Styling', 'Invitations', 'Logistics'],
    'corporate': ['Venue', 'Catering', 'AV & Production', 'Branding', 'Speaker & Talent', 'Registration', 'Logistics'],
    'birthday': ['Venue', 'Food & Cake', 'Decor', 'Entertainment', 'Photography', 'Return Gifts', 'Invitations', 'Logistics'],
}

BASE_SPLITS = {
    'wedding': np.array([0.27, 0.22, 0.14, 0.10, 0.08, 0.06, 0.03, 0.10]),
    'corporate': np.array([0.24, 0.18, 0.20, 0.08, 0.12, 0.05, 0.13]),
    'birthday': np.array([0.20, 0.25, 0.15, 0.12, 0.08, 0.07, 0.03, 0.10]),
}

CITY_FACTOR = {
    'bangalore': 1.10,
    'mumbai': 1.18,
    'delhi': 1.15,
    'hyderabad': 1.03,
    'chennai': 1.01,
    'pune': 1.00,
}


@dataclass
class BudgetPrediction:
    allocations: List[Dict[str, float]]
    total_predicted: float
    savings_tip: str


def _normalize(values: np.ndarray) -> np.ndarray:
    values = np.maximum(values, 0.01)
    return values / values.sum()


def _synthetic_rows(event_type: str, n: int = 320):
    rows = []
    targets = []
    categories = CATEGORIES[event_type]
    base = BASE_SPLITS[event_type]
    for _ in range(n):
        budget = random.randint(150000, 2500000)
        guests = random.randint(30, 1200)
        city = random.choice(list(CITY_FACTOR.keys()))
        vibe = random.choice(['luxury', 'balanced', 'budget', 'premium-minimal'])
        outdoor = random.choice([0, 1])
        city_mult = CITY_FACTOR.get(city, 1.0)

        noise = np.random.normal(0, 0.02, size=len(base))
        split = base.copy() + noise
        if vibe == 'luxury':
            split[0] += 0.03
            if 'Decor' in categories:
                split[categories.index('Decor')] += 0.02
        if vibe == 'budget':
            split[-1] += 0.02
            split[0] -= 0.03
        if outdoor and 'Decor' in categories:
            split[categories.index('Decor')] += 0.03
        split = _normalize(split)
        target = split * budget * city_mult
        rows.append(
            {
                'event_type': event_type,
                'city': city,
                'guest_count': guests,
                'budget': budget,
                'vibe': vibe,
                'outdoor': outdoor,
            }
        )
        targets.append(target)
    return rows, targets


@lru_cache(maxsize=3)
def train_budget_model(event_type: str):
    import pandas as pd

    rows, targets = _synthetic_rows(event_type)
    df = pd.DataFrame(rows)
    y = np.vstack(targets)

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), ['city', 'vibe', 'event_type']),
            ('num', StandardScaler(), ['guest_count', 'budget', 'outdoor']),
        ]
    )

    model = Pipeline(
        steps=[
            ('preprocessor', preprocessor),
            ('regressor', MultiOutputRegressor(RandomForestRegressor(n_estimators=120, random_state=42))),
        ]
    )
    model.fit(df, y)
    return model


def predict_budget_split(event_type: str, city: str, budget: int, preferences: str) -> BudgetPrediction:
    import pandas as pd

    model = train_budget_model(event_type)
    text = preferences.lower()
    vibe = 'balanced'
    if any(word in text for word in ['luxury', 'premium', 'grand']):
        vibe = 'luxury'
    elif any(word in text for word in ['budget', 'simple']):
        vibe = 'budget'
    elif any(word in text for word in ['minimal', 'elegant']):
        vibe = 'premium-minimal'

    outdoor = 1 if any(word in text for word in ['outdoor', 'garden', 'open air']) else 0
    guest_count = 300 if event_type == 'wedding' else 180 if event_type == 'corporate' else 60

    sample = pd.DataFrame(
        [
            {
                'event_type': event_type,
                'city': city.lower(),
                'guest_count': guest_count,
                'budget': budget,
                'vibe': vibe,
                'outdoor': outdoor,
            }
        ]
    )

    pred = model.predict(sample)[0]
    pred = np.maximum(pred, 1000)
    categories = CATEGORIES[event_type]
    total = float(pred.sum())
    allocations = []
    for category, amount in zip(categories, pred):
        allocations.append(
            {
                'category': category,
                'amount': round(float(amount), 2),
                'percent': round(float(amount / total * 100), 2),
            }
        )

    if total > budget * 1.05:
        savings_tip = 'Predicted spend is above budget. Reduce venue or decor scope, or shift 10-15% of spend to value vendors.'
    elif total < budget * 0.9:
        savings_tip = 'Predicted spend is under budget. Reserve the surplus for contingency, guest comfort, or premium photography.'
    else:
        savings_tip = 'Budget is well balanced. Keep a 5-8% contingency reserve and lock high-impact vendors early.'

    return BudgetPrediction(allocations=allocations, total_predicted=round(total, 2), savings_tip=savings_tip)
