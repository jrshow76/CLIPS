export interface SectorFlowPoint {
  /** epoch ms */
  ts: number;
  /** 자금 순유입(억 원) */
  net: number;
}

export interface SectorFlowSeries {
  code: string;
  name: string;
  points: SectorFlowPoint[];
}

export interface SectorRotation {
  from_sector: string;
  to_sector: string;
  flow_value: number;
  /** -1 ~ 1 사이 강도 */
  intensity: number;
}
