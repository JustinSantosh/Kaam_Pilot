/** Display only: the backend computes every amount, the frontend formats paise (D-005). */
export function formatPaise(paise: number): string {
  const sign = paise < 0 ? "-" : "";
  const abs = Math.abs(paise);
  const rupees = Math.floor(abs / 100).toString();
  const rem = (abs % 100).toString().padStart(2, "0");
  let digits = rupees;
  if (rupees.length > 3) {
    const tail = rupees.slice(-3);
    let head = rupees.slice(0, -3);
    const groups: string[] = [];
    while (head.length > 2) {
      groups.unshift(head.slice(-2));
      head = head.slice(0, -2);
    }
    if (head) groups.unshift(head);
    digits = [...groups, tail].join(",");
  }
  return `${sign}₹${digits}.${rem}`;
}

export function formatRate(bp: number): string {
  return `${bp / 100}%`;
}
