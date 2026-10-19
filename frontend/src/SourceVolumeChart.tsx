import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

/** The buyer journey does not need to download/parse the analytics library. */
export default function SourceVolumeChart({
  data,
}: {
  data: { name: string; recibidas: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        layout="vertical"
        margin={{ left: 0, right: 24, top: 12, bottom: 12 }}
        accessibilityLayer
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="name"
          width={138}
          tick={{ fontSize: 11 }}
          interval={0}
        />
        <Tooltip />
        <Bar
          isAnimationActive={false}
          name="Recibidas"
          dataKey="recibidas"
          fill="#635bff"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
