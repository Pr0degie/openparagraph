import { describe, it, expect } from 'vitest'
import { parseYear, isInTimeWindow } from './timefilter'

describe('parseYear', () => {
  it('parses the year from an ISO date', () => {
    expect(parseYear('2005-03-10')).toBe(2005)
  })
  it('returns null for null / empty', () => {
    expect(parseYear(null)).toBeNull()
    expect(parseYear('')).toBeNull()
  })
  it('returns null for the 0000 placeholder', () => {
    expect(parseYear('0000-01-01')).toBeNull()
  })
})

describe('isInTimeWindow', () => {
  it('shows a still-living law born before the window (born ≤ to, death = null)', () => {
    expect(isInTimeWindow(1990, null, 2000, 2010)).toBe(true)
  })
  it('hides a law that died before the window', () => {
    expect(isInTimeWindow(1990, 1995, 2000, 2010)).toBe(false)
  })
  it('shows a law born inside the window', () => {
    expect(isInTimeWindow(2005, null, 2000, 2010)).toBe(true)
  })
  it('hides a law born after the window', () => {
    expect(isInTimeWindow(2015, null, 2000, 2010)).toBe(false)
  })
  it('shows a law whose lifespan overlaps the window on both ends', () => {
    expect(isInTimeWindow(1990, 2005, 2000, 2010)).toBe(true)
  })
  it('shows a law with both dates unknown', () => {
    expect(isInTimeWindow(null, null, 2000, 2010)).toBe(true)
  })
  it('treats death exactly at window start as overlapping (inclusive)', () => {
    expect(isInTimeWindow(1990, 2000, 2000, 2010)).toBe(true)
  })
  it('treats birth exactly at window end as overlapping (inclusive)', () => {
    expect(isInTimeWindow(2010, null, 2000, 2010)).toBe(true)
  })
})
