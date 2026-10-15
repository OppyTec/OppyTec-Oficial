# OppyTec — Documentación Maestra y Especificaciones del Sistema (Specs)

> **Versión del Sistema:** OppyTec v2.0  
> **Estado General:** Documentación Base para Refactorización Progresiva  
> **Ecosistema:** SaaS Multi-Tenant para Gestión Gastronómica, Hotelera y Comercial  
> **Fecha de Creación / Congelamiento:** Octubre 2026  

---

## 1. Propósito y Visión General

Este directorio (`specs/`) constituye la **fuente de verdad técnica y de producto** para el proyecto **OppyTec**. Su objetivo es proporcionar una base documental completa, rigurosa y libre de ambigüedades antes de acometer cualquier proceso de refactorización o evolución del código fuente existente.

OppyTec es un software como servicio (SaaS) diseñado para resolver los desafíos críticos de abastecimiento, control de stock, escandallos (fichas técnicas de recetas), mermas, puntos de venta (POS), compras y finanzas en la industria de la hospitalidad (restaurantes, bares, hoteles, cafeterías y cadenas multilocales con estructura de Holding).

---

## 2. Mapa y Matriz de Especificaciones

La documentación se compone de 6 especificaciones canónicas más este índice maestro. Cada especificación aborda una dimensión ortogonal y complementaria del sistema:

| Archivo | Dimensión / Enfoque | Audiencia Principal | Estado | Enlace |
|---|---|---|---|---|
| **00-INDEX.md** | Índice maestro, directrices metodológicas y glosario | Todo el equipo / Agentes | **Aprobado / Activo** | [00-INDEX.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code/specs/00-INDEX.md) |
| **01-PRD.md** | Requerimientos de producto, personas, casos de uso, alcance MVP y edge cases | Product Owners, Desarrolladores | **Documentado** | [01-PRD.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code/specs/01-PRD.md) |
| **02-TRD.md** | Stack técnico, infraestructura, servicios de terceros, no-funcionales y entorno | Tech Leads, Backend/DevOps | **Documentado** | [02-TRD.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code/specs/02-TRD.md) |
| **03-USER-FLOWS.md** | Árbol de rutas, recorridos de usuario (User Journeys) y gestión de estados UI | Frontend, UX/UI, QA | **Documentado** | [03-USER-FLOWS.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code/specs/03-USER-FLOWS.md) |
| **04-DESIGN-SYSTEM.md** | Tokens de color, tipografía, componentes UI base, layout y accesibilidad | Diseñadores, Frontend | **Documentado** | [04-DESIGN-SYSTEM.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code/specs/04-DESIGN-SYSTEM.md) |
| **05-DATABASE-SCHEMA.md** | Esquemas PostgreSQL (Público vs Tenant), contratos de datos y autenticación | Backend, DBAs, Seguridad | **Documentado** | [05-DATABASE-SCHEMA.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code/specs/05-DATABASE-SCHEMA.md) |
| **06-IMPLEMENTATION-PLAN.md** | Secuencia cronológica de refactorización, checklists y validación por fase | Ingenieros, Agentes de IA | **Documentado** | [06-IMPLEMENTATION-PLAN.md](file:///home/jcampillay/WorkArea/OppyTec/OppyTec-Code/specs/06-IMPLEMENTATION-PLAN.md) |

---

## 3. Principio de No Modificación de Código Existente

Durante la fase de preparación y especificación:
1. **Inviolabilidad del código base:** Ningún archivo de `OppyTec_Backend` ni de `OppyTec_Frontend` debe ser modificado, eliminado o renombrado hasta que el plan de implementación esté completamente consensuado y validado.
2. **Consultas de sólo lectura:** Cualquier análisis técnico debe realizarse mediante inspección estática o comprobación no destructiva.
3. **Alineación previa:** Toda propuesta de cambio futura deberá justificarse referenciando explícitamente la sección correspondiente de estas specs.

---

## 4. Reglas Técnicas Permanentes (`.agent/rules/`)

Para asegurar la calidad de código y la coherencia durante el proceso, se establecen directrices inmutables en `.agent/rules/`:
- **Clean Architecture & Separación de Capas:** Dominio desacoplado de frameworks e infraestructura.
- **Tipado Estricto (Zero-Any Policy):** Pydantic v2 en Python (FastAPI) y tipado estricto en TypeScript (React 19).
- **Aislamiento Multi-Tenant Estricto:** Ejecución obligatoria dentro del esquema PostgreSQL asignado a la sucursal activa.
- **Seguridad en Profundidad (Zero-Trust):** Validación de firmas Magic Bytes para archivos, saneamiento contra ataques XSS y políticas CORS/CSRF estrictas.

---

## 5. Glosario de Términos del Dominio OppyTec

- **Holding:** Grupo empresarial matriz que agrupa una o más entidades legales y sus correspondientes locales comerciales o sucursales.
- **Entidad Legal:** Persona jurídica o razón social (con RUT/Tax ID) bajo la cual operan los establecimientos.
- **Tenant (Sucursal / Inquilino):** Establecimiento físico individual (ej. *Restaurante Pacífico Centro*). En la base de datos, cada tenant cuenta con un esquema de PostgreSQL independiente.
- **Bodega:** Espacio físico o virtual donde se almacena mercancía (ej. Bodega Principal, Cocina Caliente, Barra 1, Cámara de Congelado).
- **Producto / Insumo:** Ítem individual del catálogo con costo unitario, unidad de medida (UOM), factor de conversión y stock mínimo.
- **Escandallo / Receta:** Fórmula de producción culinaria que combina ingredientes en cantidades determinadas para obtener un plato o cóctel con costo calculado.
- **Merma:** Pérdida no recuperable de stock debido a caducidad, rotura, error de preparación o deterioro, que requiere justificación y autorización.
- **Conteo Físico (Auditoría):** Proceso de cotejo entre el inventario teórico del sistema y las existencias reales en estantería.
- **Oppy Bot:** Motor de asistencia impulsado por Inteligencia Artificial (LLM + RAG vectorial) para consultas operativas, auditorías rápidas y alertas predictivas.
