export function startCase(value: string) {
  return value
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^\w/, (char) => char.toUpperCase())
}

export function stringifyJson(value: unknown) {
  return value == null ? '' : JSON.stringify(value, null, 2)
}
