"""
Centralized Department Taxonomy and Mapping Configuration for SPIN Portal (Backend).
Ensures consistent canonical department names across authentication, API responses, and database queries.
"""

from typing import List, Optional

CANONICAL_DEPARTMENTS = [
    "Municipality",
    "Water Supply",
    "Electricity",
    "Healthcare",
    "Public Safety & Police",
    "Public Transport",
    "Education",
    "Other",
]

DEPARTMENT_ALIASES = {
    "municipality": "Municipality",
    "municipal": "Municipality",
    "municipal infrastructure & public works": "Municipality",
    "public works department (pwd)": "Municipality",
    "pwd": "Municipality",
    "waste management": "Municipality",
    "water supply": "Water Supply",
    "water supply & sanitation board": "Water Supply",
    "water": "Water Supply",
    "electricity": "Electricity",
    "electricity/power": "Electricity",
    "state power distribution corp": "Electricity",
    "power": "Electricity",
    "healthcare": "Healthcare",
    "healthcare & hospitals": "Healthcare",
    "public safety & police": "Public Safety & Police",
    "public safety & law enforcement": "Public Safety & Police",
    "police": "Public Safety & Police",
    "public transport": "Public Transport",
    "public transport (bus/metro/trains)": "Public Transport",
    "transport": "Public Transport",
    "education": "Education",
    "education (public schools)": "Education",
    "other": "Other",
}

CATEGORY_TO_DEPARTMENT = {
    "Water Supply": "Water Supply",
    "Roads & Potholes": "Municipality",
    "Drainage / Flooding": "Municipality",
    "Drainage & Flooding": "Municipality",
    "Electricity": "Electricity",
    "Electricity/Power": "Electricity",
    "Waste Management": "Municipality",
    "Waste Management & Sanitation": "Municipality",
    "Street Lighting": "Municipality",
    "Public Transport": "Public Transport",
    "Public Transport (Bus/Metro/Trains)": "Public Transport",
    "Sanitation": "Municipality",
    "Public Infrastructure": "Municipality",
    "Healthcare & Hospitals": "Healthcare",
    "Education (Public Schools)": "Education",
    "Public Safety & Law Enforcement": "Public Safety & Police",
    "Housing & Urban Development": "Municipality",
    "Environment & Trees": "Municipality",
    "Animal & Street Livestock": "Municipality",
    "Other": "Other",
}

DEPARTMENT_TO_CATEGORIES = {
    "Municipality": [
        "Roads & Potholes",
        "Drainage / Flooding",
        "Drainage & Flooding",
        "Waste Management",
        "Waste Management & Sanitation",
        "Street Lighting",
        "Sanitation",
        "Public Infrastructure",
        "Housing & Urban Development",
        "Environment & Trees",
        "Animal & Street Livestock",
    ],
    "Water Supply": ["Water Supply"],
    "Electricity": ["Electricity", "Electricity/Power"],
    "Healthcare": ["Healthcare & Hospitals"],
    "Public Safety & Police": ["Public Safety & Law Enforcement"],
    "Public Transport": ["Public Transport", "Public Transport (Bus/Metro/Trains)"],
    "Education": ["Education (Public Schools)"],
    "Other": [
        "Other",
        "Banking & Financial Services",
        "Pension & Social Security",
        "Insurance Claims",
        "Employment & Training",
        "Government Schemes & Subsidies",
        "Telecom & Mobile Network",
    ],
}


def normalize_department(dept_str: Optional[str]) -> Optional[str]:
    """Normalizes any department string or alias into its canonical form."""
    if not dept_str:
        return None
    cleaned = dept_str.strip().lower()
    if cleaned in DEPARTMENT_ALIASES:
        return DEPARTMENT_ALIASES[cleaned]
    for dept in CANONICAL_DEPARTMENTS:
        if cleaned in dept.lower() or dept.lower() in cleaned:
            return dept
    return "Other"


def get_department_for_category(category: Optional[str]) -> str:
    """Returns the canonical department responsible for a given grievance category."""
    if not category:
        return "Other"
    if category in CATEGORY_TO_DEPARTMENT:
        return CATEGORY_TO_DEPARTMENT[category]
    return normalize_department(category) or "Other"


def get_categories_for_department(dept_str: Optional[str]) -> List[str]:
    """Returns the list of categories belonging to a canonical department."""
    canonical = normalize_department(dept_str)
    if not canonical:
        return []
    return DEPARTMENT_TO_CATEGORIES.get(canonical, [])


def matches_department(
    grievance_dept: Optional[str] = None,
    grievance_category: Optional[str] = None,
    grievance_domain: Optional[str] = None,
    staff_dept: Optional[str] = None,
) -> bool:
    """Checks if a grievance record belongs to a specified staff department."""
    canonical_staff = normalize_department(staff_dept)
    if not canonical_staff:
        return False

    canonical_grievance_dept = normalize_department(grievance_dept)
    if canonical_grievance_dept and canonical_grievance_dept == canonical_staff:
        return True

    dept_from_cat = get_department_for_category(grievance_category)
    if dept_from_cat == canonical_staff:
        return True

    dept_from_dom = normalize_department(grievance_domain)
    if dept_from_dom == canonical_staff:
        return True

    return False
