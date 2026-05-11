from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .database import get_connection
from .ml import predict_budget_split
from .rag import answer_query

EVENT_PHASES = {
    'wedding': [
        ('6-8 months before', ['Finalize budget and guest count', 'Shortlist venues', 'Book venue or planner', 'Identify theme and rituals']),
        ('4-6 months before', ['Lock caterer', 'Book decor', 'Finalize photographer and makeup', 'Start invitation design']),
        ('2-3 months before', ['Send save-the-dates', 'Plan guest stay and transport', 'Confirm entertainment', 'Book wedding outfits']),
        ('2-4 weeks before', ['Freeze headcount', 'Share vendor schedules', 'Make payment tracker', 'Run family coordination meeting']),
        ('Event week', ['Create minute-by-minute ceremony flow', 'Confirm arrivals and logistics', 'Prepare emergency kit', 'Assign on-ground coordinators']),
    ],
    'corporate': [
        ('8-10 weeks before', ['Define objective and KPIs', 'Estimate audience size', 'Lock venue and date options', 'Map speaker shortlist']),
        ('6-8 weeks before', ['Confirm AV scope', 'Create registration workflow', 'Build brand assets', 'Lock catering plan']),
        ('3-5 weeks before', ['Publish invites and reminders', 'Finalize run-of-show', 'Align sponsor collateral', 'Test production requirements']),
        ('1-2 weeks before', ['Brief emcee and speakers', 'Freeze seating and badges', 'Plan lead capture', 'Dry-run all cue points']),
        ('Event week', ['Monitor attendee support', 'Run onsite checklist', 'Capture media and feedback', 'Review KPI dashboard']),
    ],
    'birthday': [
        ('4-6 weeks before', ['Choose theme and guest list', 'Book venue or home setup', 'Reserve cake and food', 'Shortlist entertainment']),
        ('2-4 weeks before', ['Lock decor', 'Send invites', 'Confirm activity flow', 'Arrange return gifts']),
        ('1 week before', ['Confirm final guest count', 'Prepare photo corner', 'Check weather backup', 'Create music playlist']),
        ('Event day', ['Decor setup', 'Food arrival check', 'Cake and activity coordination', 'Guest welcome and photos']),
    ],
}

CHECKLISTS = {
    'wedding': ['Budget sheet', 'Guest list', 'Venue contract', 'Catering menu', 'Decor moodboard', 'Photo shot list', 'Bride or groom schedule', 'Transport chart', 'Vendor payment tracker'],
    'corporate': ['Event brief', 'Stakeholder list', 'Venue contract', 'Registration page', 'Speaker kit', 'AV checklist', 'Branding assets', 'Catering count', 'Feedback form'],
    'birthday': ['Theme board', 'Guest list', 'Cake order', 'Food order', 'Decor setup sheet', 'Games and activities', 'Return gifts', 'Photography plan'],
}


@dataclass
class AgentOutput:
    planner: Dict
    optimizer: Dict
    researcher: Dict
    vendors: List[Dict]


class ResearchAgent:
    def run(self, question: str, event_type: str) -> Dict:
        result = answer_query(question or f'Best planning approach for {event_type}', event_type)
        return {'answer': result.answer, 'sources': result.sources}


class BudgetAgent:
    def run(self, event_type: str, city: str, budget: int, preferences: str) -> Dict:
        pred = predict_budget_split(event_type, city, budget, preferences)
        return {
            'allocations': pred.allocations,
            'predicted_total': pred.total_predicted,
            'savings_tip': pred.savings_tip,
        }


class PlannerAgent:
    def run(self, event_type: str, city: str, budget: int, preferences: str) -> Dict:
        phases = EVENT_PHASES[event_type]
        checklist = CHECKLISTS[event_type]
        vendor_categories = self._vendor_categories(event_type)
        timeline = []
        for label, tasks in phases:
            phase_tasks = list(tasks)
            if city.lower() == 'bangalore':
                phase_tasks.append('Factor city traffic into vendor arrival buffers')
            if 'outdoor' in preferences.lower() or 'garden' in preferences.lower():
                phase_tasks.append('Prepare a weather backup and canopy plan')
            timeline.append({'phase': label, 'tasks': phase_tasks})

        summary = (
            f"A {event_type} in {city} with a budget of ₹{budget:,.0f} and preferences '{preferences}' should prioritize "
            f"{vendor_categories[0]} while keeping a contingency reserve."
        )
        return {
            'summary': summary,
            'timeline': timeline,
            'checklist': checklist,
            'vendor_categories': vendor_categories,
        }

    def _vendor_categories(self, event_type: str) -> List[str]:
        conn = get_connection()
        try:
            rows = conn.execute(
                'SELECT category FROM vendor_categories WHERE event_type = ? ORDER BY priority ASC',
                (event_type,),
            ).fetchall()
            return [row['category'] for row in rows]
        finally:
            conn.close()


class VendorRecommender:
    def run(self, event_type: str, city: str, budget_allocations: List[Dict], preferences: str) -> List[Dict]:
        budget_map = {item['category']: item['amount'] for item in budget_allocations}
        conn = get_connection()
        try:
            rows = conn.execute('SELECT * FROM vendors WHERE LOWER(city) = LOWER(?)', (city,)).fetchall()
            vendors = [dict(row) for row in rows]
        finally:
            conn.close()

        pref_tokens = {token.strip().lower() for token in preferences.replace(',', ' ').split() if token.strip()}
        scored = []
        for vendor in vendors:
            event_types = {item.strip() for item in vendor['event_types'].split(',')}
            if event_type not in event_types:
                continue
            category_budget = budget_map.get(vendor['category'], max(budget_map.values()) * 0.1 if budget_map else vendor['base_price'])
            affordability = max(0, 1 - abs(vendor['base_price'] - category_budget) / max(category_budget, 1))
            tags = {tag.strip().lower() for tag in vendor['tags'].split(',')}
            tag_match = len(pref_tokens & tags) / max(len(pref_tokens), 1)
            score = vendor['rating'] * 0.45 + affordability * 3.5 + tag_match * 2.0
            scored.append((score, vendor))

        scored.sort(key=lambda item: item[0], reverse=True)
        selected = []
        seen_categories = set()
        for score, vendor in scored:
            if vendor['category'] in seen_categories:
                continue
            selected.append(
                {
                    'name': vendor['name'],
                    'category': vendor['category'],
                    'city': vendor['city'],
                    'base_price': vendor['base_price'],
                    'rating': vendor['rating'],
                    'tags': vendor['tags'].split(','),
                    'match_score': round(score, 2),
                }
            )
            seen_categories.add(vendor['category'])
            if len(selected) >= 6:
                break
        return selected


class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.budget = BudgetAgent()
        self.research = ResearchAgent()
        self.vendors = VendorRecommender()

    def run(self, event_type: str, city: str, budget: int, preferences: str, question: str) -> AgentOutput:
        planner_output = self.planner.run(event_type, city, budget, preferences)
        optimizer_output = self.budget.run(event_type, city, budget, preferences)
        researcher_output = self.research.run(question, event_type)
        vendor_output = self.vendors.run(event_type, city, optimizer_output['allocations'], preferences)
        return AgentOutput(
            planner=planner_output,
            optimizer=optimizer_output,
            researcher=researcher_output,
            vendors=vendor_output,
        )
