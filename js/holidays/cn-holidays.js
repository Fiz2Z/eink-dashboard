/**
 * 中国法定节假日与调休（国务院办公厅通知）
 *
 * 2026 年依据：
 * https://www.beijing.gov.cn/cs/gncs/zcwj/202603/t20260327_4568275.html
 * 国办发明电〔2025〕7号《国务院办公厅关于2026年部分节假日安排的通知》
 *
 * rest  : 放假调休休息日（含周末并入假期的日子）
 * work  : 调休上班日（周末上班）
 * labels: 格子内小字（除夕/春节等）
 */

/** @typedef {{ id: string, name: string, days: number, rest: string[], work?: string[], labels?: Record<string,string> }} HolidayBlock */

/** @type {Record<number, { ganZhi: string, holidays: HolidayBlock[] }>} */
export const CN_HOLIDAYS = {
  2026: {
    ganZhi: "丙午年",
    holidays: [
      {
        id: "newyear",
        name: "元旦",
        days: 3,
        rest: ["2026-01-01", "2026-01-02", "2026-01-03"],
        work: ["2026-01-04"],
      },
      {
        id: "spring",
        name: "春节",
        days: 9,
        rest: [
          "2026-02-15",
          "2026-02-16",
          "2026-02-17",
          "2026-02-18",
          "2026-02-19",
          "2026-02-20",
          "2026-02-21",
          "2026-02-22",
          "2026-02-23",
        ],
        work: ["2026-02-14", "2026-02-28"],
        labels: {
          "2026-02-15": "除夕",
          "2026-02-16": "春节",
        },
      },
      {
        id: "qingming",
        name: "清明节",
        days: 3,
        rest: ["2026-04-04", "2026-04-05", "2026-04-06"],
      },
      {
        id: "labor",
        name: "劳动节",
        days: 5,
        rest: [
          "2026-05-01",
          "2026-05-02",
          "2026-05-03",
          "2026-05-04",
          "2026-05-05",
        ],
        work: ["2026-05-09"],
      },
      {
        id: "duanwu",
        name: "端午节",
        days: 3,
        rest: ["2026-06-19", "2026-06-20", "2026-06-21"],
      },
      {
        id: "zhongqiu",
        name: "中秋节",
        days: 3,
        rest: ["2026-09-25", "2026-09-26", "2026-09-27"],
      },
      {
        id: "guoqing",
        name: "国庆节",
        days: 7,
        rest: [
          "2026-10-01",
          "2026-10-02",
          "2026-10-03",
          "2026-10-04",
          "2026-10-05",
          "2026-10-06",
          "2026-10-07",
        ],
        work: ["2026-09-20", "2026-10-10"],
      },
    ],
  },
};

const CN_MONTHS = [
  "一月",
  "二月",
  "三月",
  "四月",
  "五月",
  "六月",
  "七月",
  "八月",
  "九月",
  "十月",
  "十一月",
  "十二月",
];

/**
 * Build lookup maps for a given year.
 * @returns {{
 *   rest: Set<string>,
 *   work: Set<string>,
 *   labels: Record<string,string>,
 *   holidayNameByDate: Record<string,string>,
 *   ganZhi: string,
 *   blocks: HolidayBlock[],
 * }}
 */
export function getHolidayIndex(year) {
  const y = CN_HOLIDAYS[year];
  const rest = new Set();
  const work = new Set();
  /** @type {Record<string,string>} */
  const labels = {};
  /** @type {Record<string,string>} */
  const holidayNameByDate = {};
  const blocks = y?.holidays || [];

  for (const h of blocks) {
    for (const d of h.rest || []) {
      rest.add(d);
      holidayNameByDate[d] = h.name;
    }
    for (const d of h.work || []) work.add(d);
    if (h.labels) Object.assign(labels, h.labels);
  }

  return {
    rest,
    work,
    labels,
    holidayNameByDate,
    ganZhi: y?.ganZhi || "",
    blocks,
  };
}

export function cnMonthName(month1to12) {
  return CN_MONTHS[month1to12 - 1] || `${month1to12}月`;
}

/** yyyy-mm-dd */
export function ymd(y, m, d) {
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

/**
 * Holiday blocks that overlap a calendar month (for footer summary).
 */
export function holidaysInMonth(year, month1to12) {
  const y = CN_HOLIDAYS[year];
  if (!y) return [];
  const prefix = `${year}-${String(month1to12).padStart(2, "0")}-`;
  return y.holidays.filter((h) =>
    (h.rest || []).some((d) => d.startsWith(prefix)) ||
    (h.work || []).some((d) => d.startsWith(prefix))
  );
}

export function supportedHolidayYears() {
  return Object.keys(CN_HOLIDAYS)
    .map(Number)
    .sort((a, b) => a - b);
}
