const LIST_KEYS = ['items', 'data', 'results'];

export function responseList(value, resourceKey) {
  if (Array.isArray(value)) return value;
  if (!value || typeof value !== 'object') return [];

  for (const key of [resourceKey, ...LIST_KEYS]) {
    if (key && Array.isArray(value[key])) return value[key];
  }

  return [];
}

export function responseRecord(value, resourceKey) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  const nested = resourceKey ? value[resourceKey] : null;
  if (nested && typeof nested === 'object' && !Array.isArray(nested)) return nested;
  const data = value.data;
  if (data && typeof data === 'object' && !Array.isArray(data)) return data;
  return value;
}
