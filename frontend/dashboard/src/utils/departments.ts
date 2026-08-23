/**
 * Centralized Department Taxonomy and Mapping Configuration for SPIN Portal.
 * Ensures consistent canonical department names across authentication, backend API, and UI dashboard.
 */

export const CANONICAL_DEPARTMENTS = [
  "Municipality",
  "Water Supply",
  "Electricity",
  "Healthcare",
  "Public Safety & Police",
  "Public Transport",
  "Education",
  "Other",
] as const;

export type DepartmentName = (typeof CANONICAL_DEPARTMENTS)[number];

// Department alias normalizer mapping legacy/variant strings to canonical department names
const DEPARTMENT_ALIASES: Record<string, DepartmentName> = {
  municipality: "Municipality",
  municipal: "Municipality",
  "municipal infrastructure & public works": "Municipality",
  "public works department (pwd)": "Municipality",
  pwd: "Municipality",
  "waste management": "Municipality",
  "water supply": "Water Supply",
  "water supply & sanitation board": "Water Supply",
  water: "Water Supply",
  electricity: "Electricity",
  "electricity/power": "Electricity",
  "state power distribution corp": "Electricity",
  power: "Electricity",
  healthcare: "Healthcare",
  "healthcare & hospitals": "Healthcare",
  "public safety & police": "Public Safety & Police",
  "public safety & law enforcement": "Public Safety & Police",
  police: "Public Safety & Police",
  "public transport": "Public Transport",
  "public transport (bus/metro/trains)": "Public Transport",
  transport: "Public Transport",
  education: "Education",
  "education (public schools)": "Education",
  other: "Other",
};

// Map each grievance category to its governing canonical department
const CATEGORY_TO_DEPARTMENT: Record<string, DepartmentName> = {
  "Water Supply": "Water Supply",
  "Roads & Potholes": "Municipality",
  "Drainage / Flooding": "Municipality",
  "Drainage & Flooding": "Municipality",
  Electricity: "Electricity",
  "Electricity/Power": "Electricity",
  "Waste Management": "Municipality",
  "Waste Management & Sanitation": "Municipality",
  "Street Lighting": "Municipality",
  "Public Transport": "Public Transport",
  "Public Transport (Bus/Metro/Trains)": "Public Transport",
  Sanitation: "Municipality",
  "Public Infrastructure": "Municipality",
  "Healthcare & Hospitals": "Healthcare",
  "Education (Public Schools)": "Education",
  "Public Safety & Law Enforcement": "Public Safety & Police",
  "Housing & Urban Development": "Municipality",
  "Environment & Trees": "Municipality",
  "Animal & Street Livestock": "Municipality",
  Other: "Other",
};

// Map each department to its constituent categories
const DEPARTMENT_TO_CATEGORIES: Record<DepartmentName, string[]> = {
  Municipality: [
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
  Electricity: ["Electricity", "Electricity/Power"],
  Healthcare: ["Healthcare & Hospitals"],
  "Public Safety & Police": ["Public Safety & Law Enforcement"],
  "Public Transport": ["Public Transport", "Public Transport (Bus/Metro/Trains)"],
  Education: ["Education (Public Schools)"],
  Other: [
    "Other",
    "Banking & Financial Services",
    "Pension & Social Security",
    "Insurance Claims",
    "Employment & Training",
    "Government Schemes & Subsidies",
    "Telecom & Mobile Network",
  ],
};

/**
 * Normalizes any department string or alias into its canonical form.
 */
export function normalizeDepartment(deptStr?: string | null): DepartmentName | null {
  if (!deptStr) return null;
  const cleaned = deptStr.trim().toLowerCase();
  if (DEPARTMENT_ALIASES[cleaned]) {
    return DEPARTMENT_ALIASES[cleaned];
  }
  for (const dept of CANONICAL_DEPARTMENTS) {
    if (cleaned.includes(dept.toLowerCase()) || dept.toLowerCase().includes(cleaned)) {
      return dept;
    }
  }
  return "Other";
}

/**
 * Returns the canonical department responsible for a given grievance category.
 */
export function getDepartmentForCategory(category?: string | null): DepartmentName {
  if (!category) return "Other";
  if (CATEGORY_TO_DEPARTMENT[category]) {
    return CATEGORY_TO_DEPARTMENT[category];
  }
  return normalizeDepartment(category) || "Other";
}

/**
 * Returns the list of categories belonging to a canonical department.
 */
export function getCategoriesForDepartment(departmentStr?: string | null): string[] {
  const canonical = normalizeDepartment(departmentStr);
  if (!canonical) return [];
  return DEPARTMENT_TO_CATEGORIES[canonical] || [];
}

/**
 * Checks if a grievance belongs to a specified staff department.
 */
export function matchesDepartment(
  grievanceDept?: string | null,
  grievanceCategory?: string | null,
  grievanceDomain?: string | null,
  staffDept?: string | null
): boolean {
  const canonicalStaffDept = normalizeDepartment(staffDept);
  if (!canonicalStaffDept) return false;

  const canonicalGrievanceDept = normalizeDepartment(grievanceDept);
  if (canonicalGrievanceDept && canonicalGrievanceDept === canonicalStaffDept) {
    return true;
  }

  const deptFromCategory = getDepartmentForCategory(grievanceCategory);
  if (deptFromCategory === canonicalStaffDept) {
    return true;
  }

  const deptFromDomain = normalizeDepartment(grievanceDomain);
  if (deptFromDomain === canonicalStaffDept) {
    return true;
  }

  return false;
}
