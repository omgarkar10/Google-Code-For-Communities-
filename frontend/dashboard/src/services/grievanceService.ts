import type {
  Grievance,
  CitizenUser,
  StaffUser,
  GrievanceStatus,
} from "../types";
import {
  normalizeDepartment,
  getDepartmentForCategory,
  matchesDepartment,
} from "../utils/departments";

const STORAGE_GRIEVANCES_KEY = "spin_grievances_v1";
const STORAGE_CITIZEN_KEY = "spin_citizen_user_v1";
const STORAGE_STAFF_KEY = "spin_staff_user_v1";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8080/api";

const INITIAL_SEED_GRIEVANCES: Grievance[] = [
  {
    id: "SPIN-2026-884102",
    citizenId: "cit-001",
    citizenName: "Rohan Sharma",
    citizenPhone: "+919876543210",
    category: "Water Supply",
    issueType: "Pipeline leakage / burst",
    severity: "Critical",
    startDate: "2026-08-10",
    frequency: "Continuous",
    description: "Major water pipeline leakage near Sector 4 Water Tank, resulting in heavy water wastage and loss of supply to 5,000 households.",
    location: {
      lat: 18.5204,
      lng: 73.8567,
      address: "Main Sector 4 Water Tank Road",
      district: "Pune",
      state: "Maharashtra",
      pinCode: "411001",
      isVerified: true,
    },
    evidence: { photos: [] },
    aiAnalysis: {
      category: "Water Supply",
      issue: "Pipeline leakage",
      severity: "Critical",
      location: "Pune / Ward 14",
      confidence: 96,
      nearbyGrievances: 37,
      redZone: true,
      reasoning: "Spatial correlation identified 37 water grievances within 12 km².",
    },
    status: "UNDER_REVIEW",
    department: "Water Supply",
    assignedTo: "Executive Engineer (Water)",
    createdAt: "12 Aug 2026, 10:30 AM",
    updatedAt: "14 Aug 2026, 02:15 PM",
    timeline: [],
    decisionStatus: "PENDING",
  },
  {
    id: "SPIN-2026-339104",
    citizenId: "cit-002",
    citizenName: "Priya Patel",
    citizenPhone: "+919812345678",
    category: "Roads & Potholes",
    issueType: "Large potholes",
    severity: "High",
    startDate: "2026-08-12",
    frequency: "Continuous",
    description: "Deep potholes on Karve Road causing traffic blockage and recurring minor accidents during monsoon.",
    location: {
      lat: 18.5074,
      lng: 73.8077,
      address: "Karve Road Signal Junction",
      district: "Pune",
      state: "Maharashtra",
      pinCode: "411004",
      isVerified: true,
    },
    evidence: { photos: [] },
    aiAnalysis: {
      category: "Roads & Potholes",
      issue: "Large potholes",
      severity: "High",
      location: "Pune / Karve Road",
      confidence: 91,
      nearbyGrievances: 18,
      redZone: false,
      reasoning: "Road damaged across 200m stretch.",
    },
    status: "SUBMITTED",
    department: "Municipality",
    assignedTo: "Chief Road Engineer",
    createdAt: "15 Aug 2026, 09:10 AM",
    updatedAt: "15 Aug 2026, 09:10 AM",
    timeline: [],
    decisionStatus: "PENDING",
  },
  {
    id: "SPIN-2026-552910",
    citizenId: "cit-003",
    citizenName: "Amit Kumar",
    citizenPhone: "+919988776655",
    category: "Electricity",
    issueType: "Transformer failure / sparks",
    severity: "Critical",
    startDate: "2026-08-14",
    frequency: "Occasional",
    description: "Transformer near Viman Nagar market sparking during heavy load, causing 6-hour power blackouts.",
    location: {
      lat: 18.5679,
      lng: 73.9143,
      address: "Viman Nagar Central Market",
      district: "Pune",
      state: "Maharashtra",
      pinCode: "411014",
      isVerified: true,
    },
    evidence: { photos: [] },
    aiAnalysis: {
      category: "Electricity",
      issue: "Transformer failure",
      severity: "Critical",
      location: "Pune / Viman Nagar",
      confidence: 95,
      nearbyGrievances: 24,
      redZone: true,
      reasoning: "High-risk sparking hazard detected near commercial hub.",
    },
    status: "INSPECTION_SCHEDULED",
    department: "Electricity",
    assignedTo: "Sub-Divisional Engineer (Electrical)",
    createdAt: "16 Aug 2026, 04:45 PM",
    updatedAt: "17 Aug 2026, 11:00 AM",
    timeline: [],
    decisionStatus: "ACCEPTED",
  },
  {
    id: "SPIN-2026-771203",
    citizenId: "cit-004",
    citizenName: "Sunita Deshmukh",
    citizenPhone: "+919765432109",
    category: "Waste Management",
    issueType: "Overflowing garbage bin",
    severity: "Medium",
    startDate: "2026-08-15",
    frequency: "Daily",
    description: "Uncollected garbage overflowing near Kothrud public park creating foul odor and health hazard.",
    location: {
      lat: 18.5074,
      lng: 73.8077,
      address: "Kothrud Depot Road",
      district: "Pune",
      state: "Maharashtra",
      pinCode: "411038",
      isVerified: true,
    },
    evidence: { photos: [] },
    aiAnalysis: {
      category: "Waste Management",
      issue: "Overflowing garbage bin",
      severity: "Medium",
      location: "Pune / Kothrud",
      confidence: 88,
      nearbyGrievances: 9,
      redZone: false,
      reasoning: "Sanitation route delay flagged.",
    },
    status: "SUBMITTED",
    department: "Municipality",
    assignedTo: "Sanitation Inspector",
    createdAt: "17 Aug 2026, 08:30 AM",
    updatedAt: "17 Aug 2026, 08:30 AM",
    timeline: [],
    decisionStatus: "PENDING",
  },
];

/* Helper functions for LocalStorage management */
export function getStoredGrievances(): Grievance[] {
  const data = localStorage.getItem(STORAGE_GRIEVANCES_KEY);
  if (!data) {
    localStorage.setItem(STORAGE_GRIEVANCES_KEY, JSON.stringify(INITIAL_SEED_GRIEVANCES));
    return INITIAL_SEED_GRIEVANCES;
  }
  try {
    const list: Grievance[] = JSON.parse(data);
    // Ensure all stored grievances have a normalized department field
    return list.map((g) => ({
      ...g,
      department: normalizeDepartment(g.department) || getDepartmentForCategory(g.category),
    }));
  } catch (e) {
    return INITIAL_SEED_GRIEVANCES;
  }
}

export function clearStoredGrievances(): void {
  localStorage.removeItem(STORAGE_GRIEVANCES_KEY);
}

export function saveGrievance(grievance: Grievance): void {
  const list = getStoredGrievances();
  const canonicalDept = normalizeDepartment(grievance.department) || getDepartmentForCategory(grievance.category);
  const updatedGrievance: Grievance = {
    ...grievance,
    department: canonicalDept,
  };

  const index = list.findIndex((g) => g.id.toLowerCase() === grievance.id.toLowerCase());
  if (index >= 0) {
    list[index] = updatedGrievance;
  } else {
    list.unshift(updatedGrievance);
  }
  localStorage.setItem(STORAGE_GRIEVANCES_KEY, JSON.stringify(list));
}

export function getGrievanceById(id: string): Grievance | undefined {
  const list = getStoredGrievances();
  return list.find((g) => g.id.toLowerCase() === id.toLowerCase());
}

export async function fetchStaffGrievances(
  user: StaffUser
): Promise<{ grievances: Grievance[]; department: string | null; unassigned: boolean }> {
  const canonicalDept = normalizeDepartment(user.department);

  if (!canonicalDept) {
    return { grievances: [], department: null, unassigned: true };
  }

  const token = localStorage.getItem("staff_token");
  if (token) {
    try {
      const res = await fetch(`${API_URL}/staff/grievances`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "error" && data.message?.includes("Department not assigned")) {
          return { grievances: [], department: null, unassigned: true };
        }
        if (Array.isArray(data.grievances) && data.grievances.length > 0) {
          const apiGrievances: Grievance[] = data.grievances.map((g: any) => ({
            id: g.id || g.grievance_id,
            citizenId: g.user_id || "cit-001",
            citizenName: "Citizen",
            citizenPhone: "+919876543210",
            category: g.category || "Water Supply",
            issueType: g.original_text || g.category || "Civic Issue",
            severity: g.severity >= 8 ? "Critical" : g.severity >= 6 ? "High" : "Medium",
            startDate: g.created_at ? g.created_at.split("T")[0] : "2026-08-01",
            frequency: "Continuous",
            description: g.original_text || "Reported civic grievance.",
            location: {
              lat: g.latitude || 18.5204,
              lng: g.longitude || 73.8567,
              address: g.landmark || g.district || "Pune",
              district: g.district || "Pune",
              state: "Maharashtra",
              pinCode: "411001",
              isVerified: true,
            },
            evidence: { photos: [] },
            aiAnalysis: {
              category: g.category || "Water Supply",
              issue: g.original_text || "Civic Issue",
              severity: g.severity >= 8 ? "Critical" : g.severity >= 6 ? "High" : "Medium",
              location: g.district || "Pune",
              confidence: 94,
              nearbyGrievances: 12,
              redZone: g.severity >= 8,
              reasoning: "Automated analysis of spatial signal data.",
            },
            status: g.status || "SUBMITTED",
            department: g.department || getDepartmentForCategory(g.category),
            assignedTo: "Department Officer",
            createdAt: g.created_at ? new Date(g.created_at).toLocaleString("en-IN") : "Recent",
            updatedAt: "Recent",
            timeline: [],
            decisionStatus: "PENDING",
          }));

          return { grievances: apiGrievances, department: data.department || canonicalDept, unassigned: false };
        }
      }
    } catch (err) {
      console.warn("Failed to fetch grievances from backend API, using local database fallback:", err);
    }
  }

  // Fallback to local storage matching department
  const stored = getStoredGrievances();
  const IS_ADMIN = user.role === "Administrator" || user.role === "Policymaker";
  if (IS_ADMIN) {
    return { grievances: stored, department: "All Departments (Admin)", unassigned: false };
  }

  const filtered = stored.filter((g) =>
    matchesDepartment(g.department, g.category, undefined, canonicalDept)
  );

  return { grievances: filtered, department: canonicalDept, unassigned: false };
}

export function updateGrievanceStatus(id: string, status: GrievanceStatus, note?: string): Grievance | undefined {
  const list = getStoredGrievances();
  const g = list.find((item) => item.id.toLowerCase() === id.toLowerCase());
  if (g) {
    g.status = status;
    g.updatedAt = new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
    if (note) {
      g.staffNotes = g.staffNotes || [];
      g.staffNotes.push(`[${g.updatedAt}] ${note}`);
    }
    g.timeline.push({
      date: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" }).toUpperCase(),
      title: `Status Changed to ${status.replace(/_/g, " ")}`,
      description: note || `Government department updated status to ${status}.`,
      completed: true,
    });
    saveGrievance(g);
    return g;
  }
  return undefined;
}

export function updateStaffDecision(id: string, decision: "ACCEPTED" | "MODIFIED" | "REJECTED", note?: string): Grievance | undefined {
  const list = getStoredGrievances();
  const g = list.find((item) => item.id.toLowerCase() === id.toLowerCase());
  if (g) {
    g.decisionStatus = decision;
    if (decision === "ACCEPTED") {
      g.status = "UNDER_REVIEW";
    } else if (decision === "REJECTED") {
      g.status = "RESOLVED";
    }
    g.updatedAt = new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
    if (note) {
      g.staffNotes = g.staffNotes || [];
      g.staffNotes.push(`[${g.updatedAt}] Decision (${decision}): ${note}`);
    }
    saveGrievance(g);
    return g;
  }
  return undefined;
}

export function addCitizenFeedback(id: string, resolved: boolean, rating?: number, comment?: string, reopenReason?: string): Grievance | undefined {
  const list = getStoredGrievances();
  const g = list.find((item) => item.id.toLowerCase() === id.toLowerCase());
  if (g) {
    g.feedback = {
      resolved,
      rating,
      comment,
      reopenReason,
      submittedAt: new Date().toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" }),
    };
    if (!resolved) {
      g.status = "REOPENED";
      g.timeline.push({
        date: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" }).toUpperCase(),
        title: "Grievance Reopened by Citizen",
        description: reopenReason || "Citizen flagged that the issue persists.",
        completed: true,
      });
    } else {
      g.status = "RESOLVED";
      g.timeline.push({
        date: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" }).toUpperCase(),
        title: "Citizen Feedback Received",
        description: `Citizen marked issue as resolved (${rating || 5}/5 stars).`,
        completed: true,
      });
    }
    saveGrievance(g);
    return g;
  }
  return undefined;
}

/* User Session Helpers */
export function getStoredCitizenUser(): CitizenUser {
  const data = localStorage.getItem(STORAGE_CITIZEN_KEY);
  if (data) {
    try {
      return JSON.parse(data);
    } catch (e) {
      /* fallback below */
    }
  }
  return {
    id: "cit-001",
    name: "",
    phone: "",
    isLoggedIn: false,
  };
}

export function setStoredCitizenUser(user: CitizenUser): void {
  localStorage.setItem(STORAGE_CITIZEN_KEY, JSON.stringify(user));
}

export function clearStoredCitizenUser(): void {
  localStorage.removeItem(STORAGE_CITIZEN_KEY);
}

export function getStoredStaffUser(): StaffUser {
  const data = localStorage.getItem(STORAGE_STAFF_KEY);
  if (data) {
    try {
      const parsed = JSON.parse(data);
      return {
        ...parsed,
        department: normalizeDepartment(parsed.department) || "Municipality",
      };
    } catch (e) {
      /* fallback below */
    }
  }
  return {
    id: "staff-881",
    name: "Dr. A. V. Deshpande",
    employeeId: "MH-GOV-8812",
    email: "officer.infrastructure@pune.gov.in",
    department: "Municipality",
    role: "Department Officer",
    isLoggedIn: false,
  };
}

export function setStoredStaffUser(user: StaffUser): void {
  const canonical = {
    ...user,
    department: normalizeDepartment(user.department) || "Municipality",
  };
  localStorage.setItem(STORAGE_STAFF_KEY, JSON.stringify(canonical));
}
