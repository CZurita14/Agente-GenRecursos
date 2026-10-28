/** Formas de las respuestas de la API del P4 que usa el frontend. */

export interface Usuario {
  correo: string;
  rol: string;
}

export type Rol = 'dueno' | 'editor' | 'lector';

export interface AsignaturaResumen {
  id: string;
  nombre: string;
  codigo_pf: string;
  version_silabo: string;
  agente: string;
  rol: Rol;
  dueno: string;
}

export interface ClaseMenu {
  clase_id: string;
  numero_clase: number;
  dia: string;
  fecha: string;
  momento: number;
  momento_titulo: string;
  contenidos: string[];
  ra: string[];
  entregables: string[];
}

export interface SemanaMenu {
  numero: number;
  inicio: string;
  fin: string;
  clases: ClaseMenu[];
  cierra_momentos: number[];
}

export interface SilaboSubido {
  id: string;
  agente: string;
  menu: SemanaMenu[];
  clases_cambiadas: string[];
}

export type TipoAmbito = 'clase' | 'momento' | 'asignatura';

export interface Ambito {
  tipo: TipoAmbito;
  id: string;
}

export interface MenuAsignatura {
  id: string;
  rol: Rol;
  version_silabo: string;
  menu: SemanaMenu[];
}

export interface Catalogo {
  ambito: TipoAmbito;
  restringido: boolean;
  motivo: string | null;
  politica_ia: string | null;
  perfil_sugerido: string;
  herramientas: { id: string; recomendada: boolean }[];
}

export type EstadoTrabajo = 'en_cola' | 'en_espera' | 'generando' | 'verificando' | 'revisando'
  | 'listo' | 'requiere_revision' | 'error';

export interface TrabajoCreado {
  id: string;
  herramienta: string;
  estado: EstadoTrabajo;
  recurso_id?: string;
}

export interface Trabajo {
  id: string;
  herramienta: string;
  ambito_tipo: TipoAmbito;
  ambito_id: string;
  estado: EstadoTrabajo;
  lotes_total: number;
  lotes_hechos: number;
  recurso_id: string | null;
  error: string | null;
}

export interface RecursoResumen {
  id: string;
  trabajo_id: string;
  ambito_id: string;
  herramienta: string;
  version_silabo: string;
  estado: 'listo' | 'requiere_revision';
  revision: number;
  creado: string;
}

export interface Recurso extends RecursoResumen {
  contenido: unknown;
  evidencia: Record<string, unknown>;
  validado: boolean;
  validado_por: string | null;
  validado_en: string | null;
  silabo_actualizado: boolean;
  evidencia_vigente: boolean;
}
