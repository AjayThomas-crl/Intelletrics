"use client";

import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";
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

export interface BackendProfile {
  name: string;
  type: string;
  missing: {
    count: number;
    percentage: number;
  };
  uniqueness: {
    count: number;
    ratio: number;
  };
  statistics?: {
    mean?: number;
    median?: number;
    std?: number;
    min?: number;
    max?: number;
    q1?: number;
    q3?: number;
  };
  distribution?: {
    top_value: string | number;
    top_count: number;
  };
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
  const data = backend.labels.map((label, i) => ({
    label: String(label),
    value: backend.values[i] ?? 0,
  }));

  const config = {
    value: {
      label: backend.column,
      color: color ?? CHART_COLORS[0],
    },
  } satisfies ChartConfig;

  return { data, config };
}

function BarChartView({ chart }: { chart: BackendChart }) {
  const { data, config } = adaptChart(chart);

  return (
    <ChartContainer config={config} className="h-[220px] w-full">
      <BarChart data={data} margin={{ left: 0, right: 0, top: 4, bottom: 4 }}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          fontSize={11}
          interval={0}
          angle={data.length > 8 ? -45 : 0}
          textAnchor={data.length > 8 ? "end" : "middle"}
        />
        <ChartTooltip
          content={<ChartTooltipContent nameKey="value" />}
        />
        <Bar
          dataKey="value"
          fill={CHART_COLORS[0]}
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ChartContainer>
  );
}

function fmtStat(val: number | undefined): string {
  if (val === undefined || val === null) return "—";
  return Math.abs(val) >= 1000
    ? val.toLocaleString(undefined, { maximumFractionDigits: 1 })
    : Number.isInteger(val)
      ? val.toString()
      : val.toFixed(2);
}

function HistogramView({ chart, profile }: { chart: BackendChart; profile?: BackendProfile }) {
  const { data, config } = adaptChart(chart, CHART_COLORS[1]);

  return (
    <ChartContainer config={config} className="h-[220px] w-full">
      <BarChart data={data} margin={{ left: 0, right: 0, top: 10, bottom: 4 }} barCategoryGap={0}>
        <CartesianGrid vertical={false} />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          fontSize={11}
          interval={0}
          angle={data.length > 8 ? -45 : 0}
          textAnchor={data.length > 8 ? "end" : "middle"}
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

function ChartCard({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
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

export function ChartRenderer({ chart, profile }: { chart: BackendChart; profile?: BackendProfile }) {
  const chartType = chart.chart;
  
  switch (chartType) {
    case "bar":
      return (
        <ChartCard title={chart.column} description={chart.description}>
          <BarChartView chart={chart} />
        </ChartCard>
      );
    case "histogram":
      return (
        <ChartCard title={chart.column} description={chart.description}>
          <HistogramView chart={chart} profile={profile} />
        </ChartCard>
      );
    default:
      return (
        <ChartCard title={chart.column} description={chart.description}>
          <BarChartView chart={chart} />
        </ChartCard>
      );
  }
}
