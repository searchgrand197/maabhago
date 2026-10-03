const STORAGE_KEY = 'hms_rooms_config'
const TV_GROUPS_KEY = 'hms_tv_groups_config'

export const DEFAULT_ROOMS = [
  { code: 'room1', label: 'Room 1 – Dr. Sharma', prefix: 'A', isDefault: true },
  { code: 'room2', label: 'Room 2 – Dr. Mehta', prefix: 'B', isDefault: true },
  { code: 'room3', label: 'Room 3 – Dr. Patel', prefix: 'C', isDefault: true },
]

export function getRoomsConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_ROOMS
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || parsed.length < 3) return DEFAULT_ROOMS
    return parsed
  } catch {
    return DEFAULT_ROOMS
  }
}

export function saveRoomsConfig(rooms) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(rooms))
}

export function getTvGroupsConfig(rooms) {
  const safeRooms = Array.isArray(rooms) ? rooms : DEFAULT_ROOMS
  const defaultGroups = safeRooms.map((r, idx) => ({
    id: `tv${idx + 1}`,
    name: `TV ${idx + 1}`,
    left_room: r.code,
    right_room: null,
  }))

  try {
    const raw = localStorage.getItem(TV_GROUPS_KEY)
    if (!raw) return defaultGroups
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || !parsed.length) return defaultGroups
    // Backward-compatibility with old shape { rooms: [] }.
    return parsed.map((g, idx) => ({
      id: g.id || `tv${idx + 1}`,
      name: g.name || `TV ${idx + 1}`,
      left_room: g.left_room ?? (Array.isArray(g.rooms) ? g.rooms[0] || null : null),
      right_room: g.right_room ?? (Array.isArray(g.rooms) ? g.rooms[1] || null : null),
    }))
  } catch {
    return defaultGroups
  }
}

export function saveTvGroupsConfig(groups) {
  localStorage.setItem(TV_GROUPS_KEY, JSON.stringify(groups))
}

