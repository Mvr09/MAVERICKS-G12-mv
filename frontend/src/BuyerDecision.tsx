import type { Assessment } from './types';

export function BuyerDecision({ assessment: a }: { assessment: Assessment }) {
  return <div className="buyer-decision" aria-label={'Decisión y acción · '+a.supplier_id}>
    <strong>{a.needs_review ? 'Decisión por confirmar' : 'Análisis automático'}</strong>
    <p>{a.needs_review
      ? 'Verificar las dudas indicadas antes de dar la afectación por confirmada.'
      : a.urgent === 'Y'
        ? 'Acción inmediata: contactar al proveedor y confirmar entregas y medidas de continuidad.'
        : a.is_risk === 'Y'
          ? 'Seguimiento de compras: confirmar alcance y evolución del riesgo.'
          : 'Sin acción urgente sustentada por esta noticia.'}</p>
    {a.priority_requires_review && <small className="notice warning">Prioridad estimada: hay datos o severidad por confirmar. Esta advertencia no implica incertidumbre sobre el riesgo o la urgencia.</small>}
  </div>;
}
