type Props = { label: string; hp: number; maxHp?: number };

export default function HPBar({ label, hp, maxHp = 100 }: Props) {
  const pct = Math.max(0, Math.min(100, (hp / maxHp) * 100));
  const color = pct > 50 ? "#48bb78" : pct > 20 ? "#ed8936" : "#e53e3e";
  return (
    <div style={{ marginBottom: 8 }}>
      <span>{label}</span>
      <span style={{ float: "right" }}>{hp}</span>
      <div style={{ background: "#e2e8f0", borderRadius: 4, height: 12, marginTop: 4 }}>
        <div
          role="progressbar"
          aria-valuenow={hp}
          style={{
            width: `${pct}%`,
            height: "100%",
            backgroundColor: color,
            borderRadius: 4,
            transition: "width 0.3s",
          }}
        />
      </div>
    </div>
  );
}
