"use client";

import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";


export interface BackendChart {
  chart: string;
  column: string;
  labels: (string | number)[];
  values: number[];
  description?: string;
}

const CHART_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

/** Adapts backend {labels, values} into recharts data and a shadcn ChartConfig */
function adaptChart(backend: BackendChart, color?: string) {
  const limit = backend.chart === "bar" ? 8 : backend.labels.length;
  const data = backend.labels.slice(0, limit).map((label, i) => ({
    label: String(label),
    value: backend.values[i] ?? 0,
  }));
  if (backend.chart === "bar" && backend.labels.length > limit) {
    data.push({
      label: `Other (${backend.labels.length - limit})`,
      value: backend.values.slice(limit).reduce((total, value) => total + value, 0),
    });
  }

  const config = {
    value: { label: backend.column, color: color ?? CHART_COLORS[0] },
  } satisfies ChartConfig;

  return { data, config };
}

function BarChartView({ chart }: { chart: BackendChart }) {
  const { data, config } = adaptChart(chart);

  return (
    <ChartContainer config={config} className="h-[248px] min-w-0 w-full">
      <BarChart
        accessibilityLayer
        data={data}
        layout="vertical"
        margin={{ left: 0, right: 12, top: 4, bottom: 4 }}
      >
        <CartesianGrid horizontal={false} />
        <XAxis type="number" hide />
        <YAxis
          dataKey="label"
          type="category"
          axisLine={false}
          tickLine={false}
          tickMargin={6}
          width={86}
          tick={{ fontSize: 10 }}
          tickFormatter={(label: string) => label.length > 13 ? `${label.slice(0, 12)}…` : label}
        />
        <ChartTooltip content={<ChartTooltipContent nameKey="value" />} />
        <Bar dataKey="value" fill={CHART_COLORS[0]} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ChartContainer>
  );
}

function HistogramView({ chart }: { chart: BackendChart }) {
  const { data, config } = adaptChart(chart, CHART_COLORS[1]);

  return (
    <ChartContainer config={config} className="h-[252px] min-w-0 w-full">
      <BarChart data={data} margin={{ left: 0, right: 0, top: 10, bottom: 4 }} barCategoryGap={0}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          fontSize={11}
          interval="preserveStartEnd"
          angle={data.length > 8 ? -35 : 0}
          textAnchor={data.length > 8 ? "end" : "middle"}
          tickFormatter={(label: string) => label.length > 13 ? `${label.slice(0, 12)}…` : label}
        />
        <ChartTooltip
          content={<ChartTooltipContent nameKey="value" />}
        />
        <Bar
          dataKey="value"
          fill={CHART_COLORS[1]}
          radius={[2, 2, 0, 0]}
        />
      </BarChart>
    </ChartContainer>
  );
}

function chartDescription(chart: BackendChart) {
  if (chart.chart !== "bar" || chart.labels.length <= 8) return chart.description;
  const note = `“Other (${chart.labels.length - 8})” combines the remaining categories.`;
  return chart.description ? `${chart.description} ${note}` : note;
}

function ChartCard({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <Card className="min-w-0">
      <CardHeader className="min-w-0 pb-2">
        <CardTitle className="break-words text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="min-w-0">
        {children}
        {description && (
          <p className="mt-2 text-[11px] text-muted-foreground/70 leading-relaxed">
            {description}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export function ChartRenderer({ chart }: { chart: BackendChart }) {
  const chartType = chart.chart;
  
  switch (chartType) {
    case "bar":
      return (
        <ChartCard title={chart.column} description={chartDescription(chart)}>
          <BarChartView chart={chart} />
        </ChartCard>
      );
    case "histogram":
      return (
        <ChartCard title={chart.column} description={chartDescription(chart)}>
          <HistogramView chart={chart} />
        </ChartCard>
      );
    default:
      return (
        <ChartCard title={chart.column} description={chartDescription(chart)}>
          <BarChartView chart={chart} />
        </ChartCard>
      );
  }
}
