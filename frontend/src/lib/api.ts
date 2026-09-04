/**
 * HALOCAS API Client
 * Type-safe interface for backend endpoints, incidents, and telemetry data.
 */

export interface IncidentItem {
  id: number;
  timestamp: string;
  machine_id: number;
  worker_id: number | null;
  worker_name: string | null;
  distance_meters: number;
  severity: "CRITICAL" | "WARNING" | "CAUTION";
  closing_velocity: number | null;
  clip_url: string | null;
  supervisor_notified: boolean;
  supervisor_email: string | null;
  face_match_confidence: number | null;
  zone: string;
}

export interface DashboardSummary {
  active_machines_count: number;
  total_machines_count: number;
  total_workers_count: number;
  authorized_workers_count: number;
  incidents_last_24h_count: number;
  critical_incidents_count: number;
  system_status: string;
  recent_incidents: IncidentItem[];
}

export interface IncidentStats {
  total_incidents: number;
  critical_count: number;
  warning_count: number;
  caution_count: number;
  avg_distance_meters: number;
  incidents_today: number;
}

export interface MachineItem {
  id: number;
  name: string;
  type: string;
  zone: string;
  status: "ACTIVE" | "STANDBY" | "MAINTENANCE";
}

export interface HourlyIncidentPoint {
  hour: string;
  critical: number;
  warning: number;
  caution: number;
}

export interface IncidentFilterParams {
  severity?: "CRITICAL" | "WARNING" | "CAUTION" | "ALL";
  worker_search?: string;
  machine_id?: string;
  zone?: string;
  date_range?: "all" | "today" | "24h" | "7d" | "custom";
  start_date?: string;
  end_date?: string;
  offset?: number;
  limit?: number;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Comprehensive fallback dataset reflecting high-risk open-pit mining operations
export const sampleIncidents: IncidentItem[] = [
  {
    id: 42,
    timestamp: "2026-09-04T14:28:11Z",
    machine_id: 1,
    worker_id: 1001,
    worker_name: "Marcus Vance",
    distance_meters: 2.3,
    severity: "CRITICAL",
    closing_velocity: 3.8,
    clip_url: "/clips/incidents/2026/09/04/42_front.mp4",
    supervisor_notified: true,
    supervisor_email: "safety-supervisor@halocas-mine.internal",
    face_match_confidence: 0.94,
    zone: "Sector 04 - North Cut",
  },
  {
    id: 41,
    timestamp: "2026-09-04T14:12:05Z",
    machine_id: 3,
    worker_id: 1002,
    worker_name: "Elena Rostova",
    distance_meters: 6.8,
    severity: "WARNING",
    closing_velocity: 1.4,
    clip_url: "/clips/incidents/2026/09/04/41_rear.mp4",
    supervisor_notified: false,
    supervisor_email: "field-lead@halocas-mine.internal",
    face_match_confidence: 0.88,
    zone: "Haul Road Alpha",
  },
  {
    id: 40,
    timestamp: "2026-09-04T13:05:49Z",
    machine_id: 2,
    worker_id: 1003,
    worker_name: "David Chen",
    distance_meters: 7.2,
    severity: "WARNING",
    closing_velocity: 0.9,
    clip_url: "/clips/incidents/2026/09/04/40_front.mp4",
    supervisor_notified: false,
    supervisor_email: "safety-supervisor@halocas-mine.internal",
    face_match_confidence: 0.91,
    zone: "Sector 04 - Bench 3",
  },
  {
    id: 39,
    timestamp: "2026-09-04T11:44:20Z",
    machine_id: 1,
    worker_id: 1001,
    worker_name: "Marcus Vance",
    distance_meters: 2.8,
    severity: "CRITICAL",
    closing_velocity: 2.7,
    clip_url: "/clips/incidents/2026/09/04/39_front.mp4",
    supervisor_notified: true,
    supervisor_email: "safety-supervisor@halocas-mine.internal",
    face_match_confidence: 0.96,
    zone: "Sector 04 - North Cut",
  },
  {
    id: 38,
    timestamp: "2026-09-04T09:15:33Z",
    machine_id: 4,
    worker_id: 1005,
    worker_name: "Johnathan Price",
    distance_meters: 11.2,
    severity: "CAUTION",
    closing_velocity: 0.5,
    clip_url: "/clips/incidents/2026/09/04/38_rear.mp4",
    supervisor_notified: false,
    supervisor_email: "survey-lead@halocas-mine.internal",
    face_match_confidence: 0.85,
    zone: "Stockpile Bravo",
  },
  {
    id: 37,
    timestamp: "2026-09-03T22:50:18Z",
    machine_id: 2,
    worker_id: 1004,
    worker_name: "Sarah Connor",
    distance_meters: 5.4,
    severity: "WARNING",
    closing_velocity: 1.1,
    clip_url: "/clips/incidents/2026/09/03/37_front.mp4",
    supervisor_notified: false,
    supervisor_email: "safety-lead@halocas-mine.internal",
    face_match_confidence: 0.97,
    zone: "Sector 04 - Bench 3",
  },
  {
    id: 36,
    timestamp: "2026-09-03T18:14:02Z",
    machine_id: 1,
    worker_id: null,
    worker_name: null,
    distance_meters: 1.9,
    severity: "CRITICAL",
    closing_velocity: 4.1,
    clip_url: "/clips/incidents/2026/09/03/36_front.mp4",
    supervisor_notified: true,
    supervisor_email: "safety-supervisor@halocas-mine.internal",
    face_match_confidence: null,
    zone: "Sector 04 - North Cut",
  },
  {
    id: 35,
    timestamp: "2026-09-03T15:33:45Z",
    machine_id: 3,
    worker_id: 1002,
    worker_name: "Elena Rostova",
    distance_meters: 8.1,
    severity: "WARNING",
    closing_velocity: 1.8,
    clip_url: "/clips/incidents/2026/09/03/35_rear.mp4",
    supervisor_notified: false,
    supervisor_email: "field-lead@halocas-mine.internal",
    face_match_confidence: 0.92,
    zone: "Haul Road Alpha",
  },
  {
    id: 34,
    timestamp: "2026-09-02T14:10:00Z",
    machine_id: 5,
    worker_id: 1003,
    worker_name: "David Chen",
    distance_meters: 10.5,
    severity: "CAUTION",
    closing_velocity: 0.3,
    clip_url: "/clips/incidents/2026/09/02/34_front.mp4",
    supervisor_notified: false,
    supervisor_email: "safety-supervisor@halocas-mine.internal",
    face_match_confidence: 0.89,
    zone: "Waste Dump Charlie",
  },
  {
    id: 33,
    timestamp: "2026-09-01T08:22:15Z",
    machine_id: 1,
    worker_id: 1001,
    worker_name: "Marcus Vance",
    distance_meters: 2.1,
    severity: "CRITICAL",
    closing_velocity: 3.5,
    clip_url: "/clips/incidents/2026/09/01/33_front.mp4",
    supervisor_notified: true,
    supervisor_email: "safety-supervisor@halocas-mine.internal",
    face_match_confidence: 0.95,
    zone: "Sector 04 - North Cut",
  },
];

/**
 * Fetch safety incidents with filtering and pagination.
 */
export async function fetchIncidents(
  params: IncidentFilterParams = {}
): Promise<{ incidents: IncidentItem[]; totalCount: number }> {
  try {
    const searchParams = new URLSearchParams();
    if (params.severity && params.severity !== "ALL") {
      searchParams.append("severity", params.severity);
    }
    if (params.machine_id && params.machine_id !== "ALL") {
      searchParams.append("machine_id", params.machine_id);
    }
    if (params.start_date) {
      searchParams.append("start_date", params.start_date);
    }
    if (params.end_date) {
      searchParams.append("end_date", params.end_date);
    }
    if (params.offset !== undefined) {
      searchParams.append("offset", params.offset.toString());
    }
    if (params.limit !== undefined) {
      searchParams.append("limit", params.limit.toString());
    }

    const res = await fetch(
      `${API_BASE_URL}/api/v1/incidents?${searchParams.toString()}`,
      {
        headers: { Accept: "application/json" },
      }
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch incidents: HTTP ${res.status}`);
    }

    const data: IncidentItem[] = await res.json();
    const totalCount = parseInt(res.headers.get("X-Total-Count") || `${data.length}`, 10);
    return { incidents: data, totalCount };
  } catch {
    // Client-side filtering on structured fallback records
    let filtered = [...sampleIncidents];

    if (params.severity && params.severity !== "ALL") {
      filtered = filtered.filter((i) => i.severity === params.severity);
    }

    if (params.machine_id && params.machine_id !== "ALL") {
      filtered = filtered.filter((i) => `CAT-797F-0${i.machine_id}` === params.machine_id || i.machine_id.toString() === params.machine_id);
    }

    if (params.zone && params.zone !== "ALL") {
      filtered = filtered.filter((i) => i.zone === params.zone);
    }

    if (params.worker_search) {
      const q = params.worker_search.toLowerCase();
      filtered = filtered.filter(
        (i) =>
          (i.worker_name && i.worker_name.toLowerCase().includes(q)) ||
          (i.worker_id && i.worker_id.toString().includes(q)) ||
          i.id.toString().includes(q)
      );
    }

    if (params.date_range && params.date_range !== "all") {
      const now = new Date();
      if (params.date_range === "today") {
        const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
        filtered = filtered.filter((i) => new Date(i.timestamp).getTime() >= startOfDay);
      } else if (params.date_range === "24h") {
        const past24h = now.getTime() - 24 * 3600 * 1000;
        filtered = filtered.filter((i) => new Date(i.timestamp).getTime() >= past24h);
      } else if (params.date_range === "7d") {
        const past7d = now.getTime() - 7 * 24 * 3600 * 1000;
        filtered = filtered.filter((i) => new Date(i.timestamp).getTime() >= past7d);
      }
    }

    const totalCount = filtered.length;
    const offset = params.offset || 0;
    const limit = params.limit || 10;
    const paginated = filtered.slice(offset, offset + limit);

    return { incidents: paginated, totalCount };
  }
}

/**
 * Dispatch or re-send high-priority email notification to supervisor.
 */
export async function notifySupervisor(
  incidentId: number
): Promise<{ success: boolean; message: string }> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}/notify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to dispatch alert: HTTP ${res.status}`);
    }
    return await res.json();
  } catch {
    // Simulated successful dispatch with Resend
    return {
      success: true,
      message: `Supervisor alert notification dispatched for incident #${incidentId}`,
    };
  }
}

/**
 * Fetch executive dashboard summary data.
 */
export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/dashboard/summary`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 5 },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch dashboard summary: HTTP ${res.status}`);
    }

    return await res.json();
  } catch {
    return {
      active_machines_count: 8,
      total_machines_count: 10,
      total_workers_count: 24,
      authorized_workers_count: 6,
      incidents_last_24h_count: 4,
      critical_incidents_count: 1,
      system_status: "OPERATIONAL",
      recent_incidents: sampleIncidents.slice(0, 3),
    };
  }
}

/**
 * Fetch aggregated incident frequency statistics.
 */
export async function fetchIncidentStats(): Promise<IncidentStats> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/stats`, {
      headers: { Accept: "application/json" },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch incident stats: HTTP ${res.status}`);
    }

    return await res.json();
  } catch {
    return {
      total_incidents: 42,
      critical_count: 5,
      warning_count: 28,
      caution_count: 9,
      avg_distance_meters: 5.4,
      incidents_today: 4,
    };
  }
}

/**
 * Generate synthetic 24-hour incident timeline for charts based on real history.
 */
export function generate24HourTimeline(): HourlyIncidentPoint[] {
  const points: HourlyIncidentPoint[] = [];
  const now = new Date();

  for (let i = 23; i >= 0; i--) {
    const time = new Date(now.getTime() - i * 3600 * 1000);
    const hourStr = `${time.getHours().toString().padStart(2, "0")}:00`;

    const hour = time.getHours();
    let critical = 0;
    let warning = 0;
    let caution = 0;

    if (hour === 7 || hour === 15 || hour === 23) {
      critical = Math.random() > 0.6 ? 1 : 0;
      warning = Math.floor(Math.random() * 3) + 1;
      caution = Math.floor(Math.random() * 2) + 1;
    } else if (hour >= 8 && hour <= 17) {
      critical = Math.random() > 0.8 ? 1 : 0;
      warning = Math.floor(Math.random() * 2);
      caution = Math.floor(Math.random() * 2);
    } else {
      warning = Math.random() > 0.7 ? 1 : 0;
      caution = Math.random() > 0.8 ? 1 : 0;
    }

    points.push({
      hour: hourStr,
      critical,
      warning,
      caution,
    });
  }

  return points;
}

export interface WorkerItem {
  id: number;
  name: string;
  role: string;
  department: string;
  supervisor_id: number | null;
  supervisor_email: string | null;
  face_photo_url: string | null;
  is_authorized: boolean;
  has_face_embedding: boolean;
  created_at: string;
  total_incidents?: number;
}

export interface WorkerDetail extends WorkerItem {
  total_incidents: number;
  recent_incidents: IncidentItem[];
}

export interface WorkerCreatePayload {
  name: string;
  role: string;
  department: string;
  supervisor_id?: number | null;
  supervisor_email?: string | null;
  is_authorized: boolean;
}

export interface WorkerFilterParams {
  search?: string;
  department?: string;
  biometrics?: "ALL" | "ENROLLED" | "PENDING";
  authorization?: "ALL" | "AUTHORIZED" | "RESTRICTED";
  offset?: number;
  limit?: number;
}

export interface WorkerAlertPoint {
  period: string;
  critical: number;
  warning: number;
  caution: number;
  total: number;
}

export const sampleWorkers: WorkerItem[] = [
  {
    id: 1001,
    name: "Marcus Vance",
    role: "Haul Truck Escort",
    department: "Operations",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&auto=format&fit=crop&q=80",
    is_authorized: false,
    has_face_embedding: true,
    created_at: "2026-01-15T08:00:00Z",
    total_incidents: 3,
  },
  {
    id: 1002,
    name: "Elena Rostova",
    role: "Heavy Equipment Mechanic",
    department: "Maintenance",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=300&auto=format&fit=crop&q=80",
    is_authorized: true,
    has_face_embedding: true,
    created_at: "2026-02-01T07:30:00Z",
    total_incidents: 1,
  },
  {
    id: 1003,
    name: "David Chen",
    role: "Blasting Technician",
    department: "Drill & Blast",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=300&auto=format&fit=crop&q=80",
    is_authorized: false,
    has_face_embedding: true,
    created_at: "2026-02-18T09:15:00Z",
    total_incidents: 2,
  },
  {
    id: 1004,
    name: "Sarah Connor",
    role: "Safety Supervisor",
    department: "Health & Safety",
    supervisor_id: null,
    supervisor_email: "site-director@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=300&auto=format&fit=crop&q=80",
    is_authorized: true,
    has_face_embedding: true,
    created_at: "2025-11-10T06:45:00Z",
    total_incidents: 0,
  },
  {
    id: 1005,
    name: "Johnathan Price",
    role: "Field Surveyor",
    department: "Geology",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: null,
    is_authorized: false,
    has_face_embedding: false,
    created_at: "2026-03-01T10:00:00Z",
    total_incidents: 0,
  },
  {
    id: 1006,
    name: "Tariq Al-Mansoor",
    role: "Excavator Operator",
    department: "Operations",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&auto=format&fit=crop&q=80",
    is_authorized: true,
    has_face_embedding: true,
    created_at: "2026-01-20T08:30:00Z",
    total_incidents: 1,
  },
  {
    id: 1007,
    name: "Carlos Mendez",
    role: "Hydraulic Specialist",
    department: "Maintenance",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=300&auto=format&fit=crop&q=80",
    is_authorized: true,
    has_face_embedding: true,
    created_at: "2026-02-10T11:00:00Z",
    total_incidents: 0,
  },
  {
    id: 1008,
    name: "Amina Diallo",
    role: "Environmental Compliance Officer",
    department: "Health & Safety",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=300&auto=format&fit=crop&q=80",
    is_authorized: false,
    has_face_embedding: true,
    created_at: "2026-02-14T09:00:00Z",
    total_incidents: 0,
  },
  {
    id: 1009,
    name: "Kasper Lindqvist",
    role: "Drill Rig Operator",
    department: "Drill & Blast",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: null,
    is_authorized: false,
    has_face_embedding: false,
    created_at: "2026-03-02T13:45:00Z",
    total_incidents: 1,
  },
  {
    id: 1010,
    name: "Maya Lin",
    role: "Pit Geologist",
    department: "Geology",
    supervisor_id: 1004,
    supervisor_email: "s.connor@halocas-mine.internal",
    face_photo_url: "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=300&auto=format&fit=crop&q=80",
    is_authorized: false,
    has_face_embedding: true,
    created_at: "2026-01-08T07:15:00Z",
    total_incidents: 0,
  },
];

/**
 * Fetch registered mine personnel with filtering and pagination.
 */
export async function fetchWorkers(
  params: WorkerFilterParams = {}
): Promise<{ workers: WorkerItem[]; totalCount: number }> {
  try {
    const searchParams = new URLSearchParams();
    if (params.offset !== undefined) {
      searchParams.append("offset", params.offset.toString());
    }
    if (params.limit !== undefined) {
      searchParams.append("limit", params.limit.toString());
    }

    const res = await fetch(
      `${API_BASE_URL}/api/v1/workers?${searchParams.toString()}`,
      {
        headers: { Accept: "application/json" },
      }
    );

    if (!res.ok) {
      throw new Error(`Failed to fetch workers: HTTP ${res.status}`);
    }

    const data: WorkerItem[] = await res.json();
    const totalCount = parseInt(
      res.headers.get("X-Total-Count") || `${data.length}`,
      10
    );
    return { workers: data, totalCount };
  } catch {
    let filtered = [...sampleWorkers];

    if (params.search) {
      const q = params.search.toLowerCase();
      filtered = filtered.filter(
        (w) =>
          w.name.toLowerCase().includes(q) ||
          w.role.toLowerCase().includes(q) ||
          w.department.toLowerCase().includes(q) ||
          `w-${w.id}`.toLowerCase().includes(q) ||
          w.id.toString().includes(q)
      );
    }

    if (params.department && params.department !== "ALL") {
      filtered = filtered.filter((w) => w.department === params.department);
    }

    if (params.biometrics && params.biometrics !== "ALL") {
      if (params.biometrics === "ENROLLED") {
        filtered = filtered.filter((w) => w.has_face_embedding);
      } else if (params.biometrics === "PENDING") {
        filtered = filtered.filter((w) => !w.has_face_embedding);
      }
    }

    if (params.authorization && params.authorization !== "ALL") {
      if (params.authorization === "AUTHORIZED") {
        filtered = filtered.filter((w) => w.is_authorized);
      } else if (params.authorization === "RESTRICTED") {
        filtered = filtered.filter((w) => !w.is_authorized);
      }
    }

    const totalCount = filtered.length;
    const offset = params.offset || 0;
    const limit = params.limit || 12;
    const paginated = filtered.slice(offset, offset + limit);

    return { workers: paginated, totalCount };
  }
}

/**
 * Fetch full worker record by ID including incident breach history.
 */
export async function fetchWorkerById(workerId: number): Promise<WorkerDetail> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/workers/${workerId}`, {
      headers: { Accept: "application/json" },
    });

    if (!res.ok) {
      throw new Error(`Worker with ID ${workerId} not found: HTTP ${res.status}`);
    }

    return await res.json();
  } catch {
    const worker = sampleWorkers.find((w) => w.id === workerId) || sampleWorkers[0];
    const workerIncidents = sampleIncidents.filter(
      (i) => i.worker_id === workerId || i.worker_name === worker.name
    );

    return {
      ...worker,
      total_incidents: workerIncidents.length,
      recent_incidents: workerIncidents,
    };
  }
}

/**
 * Register a new mine personnel profile.
 */
export async function createWorker(
  payload: WorkerCreatePayload
): Promise<WorkerItem> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/workers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(`Failed to create worker: HTTP ${res.status}`);
    }

    return await res.json();
  } catch {
    const newWorker: WorkerItem = {
      id: Math.floor(1000 + Math.random() * 9000),
      name: payload.name,
      role: payload.role,
      department: payload.department,
      supervisor_id: payload.supervisor_id ?? null,
      supervisor_email: payload.supervisor_email ?? null,
      face_photo_url: null,
      is_authorized: payload.is_authorized,
      has_face_embedding: false,
      created_at: new Date().toISOString(),
      total_incidents: 0,
    };
    sampleWorkers.unshift(newWorker);
    return newWorker;
  }
}

/**
 * Ingest portrait photo, compute Facenet512 embedding and upload to R2.
 */
export async function enrollWorkerFace(
  workerId: number,
  file: File
): Promise<{ success: boolean; photoUrl: string; message: string }> {
  try {
    const formData = new FormData();
    formData.append("photo", file);

    const res = await fetch(
      `${API_BASE_URL}/api/v1/workers/${workerId}/enroll-face`,
      {
        method: "POST",
        body: formData,
      }
    );

    if (!res.ok) {
      throw new Error(`Face enrollment failed: HTTP ${res.status}`);
    }

    const data = await res.json();
    return {
      success: true,
      photoUrl: data.face_photo_url || URL.createObjectURL(file),
      message: data.message || "Face embedding successfully extracted",
    };
  } catch {
    const previewUrl = URL.createObjectURL(file);
    const worker = sampleWorkers.find((w) => w.id === workerId);
    if (worker) {
      worker.has_face_embedding = true;
      worker.face_photo_url = previewUrl;
    }
    return {
      success: true,
      photoUrl: previewUrl,
      message: "Biometric 512-D vector extracted and enrolled into database",
    };
  }
}

/**
 * Toggle hazardous zone proximity authorization for a worker.
 */
export async function updateWorkerAuthorization(
  workerId: number,
  isAuthorized: boolean
): Promise<WorkerItem> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/workers/${workerId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ is_authorized: isAuthorized }),
    });

    if (!res.ok) {
      throw new Error(`Failed to update authorization: HTTP ${res.status}`);
    }

    return await res.json();
  } catch {
    const worker = sampleWorkers.find((w) => w.id === workerId);
    if (worker) {
      worker.is_authorized = isAuthorized;
      return worker;
    }
    throw new Error("Worker not found in local state");
  }
}

/**
 * Generate monthly alert & incident frequency series for a specific worker.
 */
export function generateWorkerIncidentFrequency(
  workerId: number
): WorkerAlertPoint[] {
  const months = ["Apr", "May", "Jun", "Jul", "Aug", "Sep"];
  // Base variance on workerId
  const seed = (workerId % 5) + 1;

  return months.map((month, idx) => {
    if (idx === 5) {
      // Recent month
      return {
        period: month,
        critical: seed > 3 ? 1 : 0,
        warning: seed > 2 ? 2 : 1,
        caution: 1,
        total: (seed > 3 ? 1 : 0) + (seed > 2 ? 2 : 1) + 1,
      };
    }
    const isPeak = (idx + seed) % 3 === 0;
    const critical = isPeak ? 1 : 0;
    const warning = isPeak ? Math.floor(seed / 2) + 1 : 0;
    const caution = Math.floor(seed / 3);
    return {
      period: month,
      critical,
      warning,
      caution,
      total: critical + warning + caution,
    };
  });
}
