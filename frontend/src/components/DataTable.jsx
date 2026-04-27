import { formatNumber } from "../utils/formatters";

function DataTable({ rows }) {
  return (
    <section className="rounded-3xl bg-slate-900 border border-slate-800 p-4 sm:p-6">
      <h2 className="text-xl font-semibold mb-4">Datos procesados</h2>

      <div className="overflow-x-auto">
        <table className="min-w-[720px] w-full text-sm">
          <thead className="text-slate-400 border-b border-slate-800">
            <tr>
              <th className="text-left py-3">Empresa</th>
              <th className="text-left py-3">Actividad</th>
              <th className="text-right py-3">Cantidad</th>
              <th className="text-right py-3">Factor</th>
              <th className="text-right py-3">Emisiones</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index} className="border-b border-slate-800/60">
                <td className="py-3">{row.empresa}</td>
                <td className="py-3">{row.actividad}</td>
                <td className="py-3 text-right">
                  {formatNumber(row.cantidad)}
                </td>
                <td className="py-3 text-right">
                  {formatNumber(row.factor_emision, 4)}
                </td>
                <td className="py-3 text-right font-semibold text-emerald-300">
                  {formatNumber(row.emisiones)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default DataTable;
