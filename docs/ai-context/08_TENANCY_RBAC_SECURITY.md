# Carbono Zero — Multi-tenancy, RBAC y seguridad

## Boundary principal

`Organizacion` es el límite principal de aislamiento del dominio moderno. Todo recurso con tenant debe pertenecer a la misma organización.

## Contexto adicional

El acceso puede estrecharse mediante obra, área operacional, workspace, membresía y rol/permisos. Un workspace nunca debe otorgar acceso cross-tenant.

## Comportamiento esperado

- recurso de otro tenant: no exponer;
- relación inválida cross-tenant: rechazar;
- falta de permiso: 403 cuando corresponda;
- recurso inexistente/no visible: 404 según contrato.

## Riesgos

Atención especial a IDs suministrados por frontend, relaciones M2M, evidencia/versión, obra/workspace, importaciones, endpoints legacy, selectores sin scope, reportes agregados, caché e IA con contexto de otro tenant.

## Evidencia

Validar tamaño, tipo, almacenamiento, acceso, ruta, tenant, checksum y versión.

## Secretos

Nunca incluir `.env` real, API keys, passwords, private keys, tokens ni credenciales en repo o documentación de IA.

## Repo público

El repositorio principal es público. No commitear datos reales de clientes, evidencia sensible o secretos.

## RBAC

Antes de mutar: autenticar → resolver organización → validar membresía → validar permiso → validar obra/workspace → validar relaciones → persistir.