/** Nombres legibles de las herramientas y cuáles se generan sin IA (P3a). */
export const NOMBRES: Record<string, string> = {
  cuestionario: 'Cuestionario',
  ficha_clase: 'Ficha de clase',
  simulacro: 'Simulacro',
  repaso_momento: 'Repaso integrador',
  guia_evidencia: 'Guía de la evidencia',
  estudio_caso: 'Estudio de caso',
  guia_producto_final: 'Guía del producto final',
  hoja_ruta: 'Hoja de ruta de la asignatura',
  autoevaluacion_rubrica: 'Autoevaluación con la rúbrica',
  autoevaluacion_final: 'Autoevaluación final',
  lista_evidencia: 'Lista de verificación de la evidencia',
};

export const SIN_IA = new Set(['hoja_ruta', 'autoevaluacion_rubrica', 'autoevaluacion_final', 'lista_evidencia']);

export const nombreHerramienta = (id: string) => NOMBRES[id] ?? id;

/** «M2-S1» → «Clase M2-S1»; «M2» → «Momento 2»; «asignatura» → «Asignatura». */
export function nombreAmbito(id: string): string {
  if (id === 'asignatura') return 'Asignatura';
  const momento = /^M(\d+)$/.exec(id);
  return momento ? `Momento ${momento[1]}` : `Clase ${id}`;
}

const DIAS: Record<string, string> = { lun: 'lun', mar: 'mar', mie: 'mié', jue: 'jue', vie: 'vie', sab: 'sáb', dom: 'dom' };
export const dia = (d: string) => DIAS[d] ?? d;

/** «2026-10-14» → «14/10» (sin depender de la zona horaria del navegador). */
export const fechaCorta = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
