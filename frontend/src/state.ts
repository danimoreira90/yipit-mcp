// The single source of truth for UI selection. Server data stays in TanStack Query.

export interface DateRange {
  start: string
  end: string
}

export interface SelectionState {
  sector: string
  q: string
  ticker: string
  kpi: string
  range: DateRange
  trajectoryOn: boolean
}

export type SelectionAction =
  | { type: 'setSector'; sector: string }
  | { type: 'setQuery'; q: string }
  | { type: 'selectCompany'; ticker: string }
  | { type: 'setKpi'; kpi: string }
  | { type: 'setRange'; range: DateRange }
  | { type: 'toggleTrajectory' }

export const initialSelection: SelectionState = {
  sector: '',
  q: '',
  ticker: '',
  kpi: '',
  range: { start: '', end: '' },
  trajectoryOn: false,
}

export function selectionReducer(
  state: SelectionState,
  action: SelectionAction,
): SelectionState {
  switch (action.type) {
    case 'setSector':
      // A new sector changes the company list, so the company/kpi selection no longer applies.
      return { ...state, sector: action.sector, ticker: '', kpi: '' }
    case 'setQuery':
      return { ...state, q: action.q }
    case 'selectCompany':
      // kpi is auto-picked once the company's estimates load (App effect).
      return { ...state, ticker: action.ticker, kpi: '' }
    case 'setKpi':
      return { ...state, kpi: action.kpi }
    case 'setRange':
      return { ...state, range: action.range }
    case 'toggleTrajectory':
      return { ...state, trajectoryOn: !state.trajectoryOn }
  }
}
