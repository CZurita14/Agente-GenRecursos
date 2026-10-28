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
