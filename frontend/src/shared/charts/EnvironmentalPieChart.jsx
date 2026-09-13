import EnvironmentalDonutChart, { DonutLegend } from "./EnvironmentalDonutChart";

/**
 * Pie variant of the shared environmental distribution chart. Keeping this
 * thin wrapper means tooltips, empty states, colours and formatting stay
 * identical to the donut used by executive dashboards.
 */
export default function EnvironmentalPieChart(props) {
  return <EnvironmentalDonutChart {...props} innerRadius={0} />;
}

export { DonutLegend };
