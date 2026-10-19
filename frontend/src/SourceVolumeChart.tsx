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
      <BarChart data={data} margin={{ left: 0, right: 10, bottom: 40 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="name"
          angle={-25}
          textAnchor="end"
          height={70}
          tick={{ fontSize: 10 }}
        />
        <YAxis allowDecimals={false} width={30} />
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
