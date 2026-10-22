# QA de subtareas logísticas — EventsFlow

## Resultado vigente tras corrección autorizada — 21 de octubre de 2026

**QA-01 corregido y verificado localmente: 138 pruebas aprobadas, 0 fallidas.**
No se eliminó ni se marcó como esperada ninguna prueba fallida. El resultado previo
de 133 aprobadas y un fallo se conserva más abajo y en su archivo de evidencia original.

### Corrección aplicada

Único archivo de producción modificado: `api/serializers.py`, clase
`SubtareaLogisticaSerializer`, método `validate_evento` (línea 175).
Si existe una instancia y el ID del evento recibido difiere de su evento actual,
se lanza ValidationError con el mensaje «No se puede cambiar el evento de una subtarea.».
La vista responde HTTP 400 antes de guardar. Esto impide trasladar una subtarea a
eventos propios o ajenos; el mismo evento sigue siendo válido. No se modificaron
vistas, modelos, autenticación ni migraciones.

### Regresión y operaciones válidas

Se conservó la prueba que detectó QA-01 y se añadieron cuatro pruebas al archivo
`api/tests/test_subtareas_qa.py`. El módulo contiene ahora 11 pruebas.

| Caso comprobado | HTTP observado | Persistencia verificada | Resultado |
| --- | --- | --- | --- |
| PATCH a evento de otra cuenta | 400 | Conserva evento original | Aprobado |
| PATCH a otro evento propio | 400 | Conserva evento original | Aprobado |
| PATCH con el mismo evento y nuevo nombre | 200 | Actualiza nombre y conserva evento | Aprobado |
| Traslado combinado con nombre, tanto a evento propio como ajeno | 400 | Registro completo idéntico, incluido actualizado_en | Aprobado |
| POST con evento ajeno en el cuerpo | 201 | Crea bajo el evento de la URL; no crea en el ajeno | Aprobado |
| Ejecución repetida | 200 | Conserva fecha, horas y nota | Aprobado |
| Eliminación propia y segunda eliminación | 204 / 404 | Libera carga y conserva otra subtarea | Aprobado |
| Consulta del progreso después de eliminar | 200 | Refleja el nuevo total | Aprobado |
| Eliminación sin sesión o con evento ajeno/incorrecto | 401 / 404 | Conserva registro | Aprobado |
| Validaciones inválidas de PATCH | 400 | Registro completo sin cambios | Aprobado |

La suite completa también aprobó la cobertura existente de creación, consulta,
actualización, eliminación, posposición, sobrecarga y autenticación.
Se mantienen los HTTP 409 para sobrecarga sin confirmar y 400 para superar 24 horas.

### Ejecución sin migraciones

Se añadió `docs/qa/ejecutar_sin_migraciones.py`, un ejecutor de apoyo que carga
`api.tests.settings_qa` y exige SQLite con NAME `:memory:`. Crea las tablas desde
los modelos mediante schema_editor; no utiliza el ejecutor de migraciones.
Prepara únicamente la cuenta demo ficticia necesaria para la prueba existente
de correo duplicado, con contraseña inutilizable. No ejecuta migraciones de datos.
Usa DiscoverRunner con failfast para detenerse ante el primer fallo.

Orden real de ejecución:

```bash
.venv/bin/python docs/qa/ejecutar_sin_migraciones.py api.tests.test_subtareas_qa
# 11 aprobadas, 0 fallidas; 0,731 segundos; salida del proceso 0.

.venv/bin/python docs/qa/ejecutar_sin_migraciones.py api.tests
# 138 aprobadas, 0 fallidas; 13,654 segundos; salida del proceso 0.
```

Evidencias íntegras:

- `docs/qa/subtareas_regresion_resultados.txt`: módulo específico.
- `docs/qa/subtareas_suite_corregida_resultados.txt`: suite completa.
- `docs/qa/subtareas_resultados.txt`: ejecución histórica con QA-01 reproducido.

No hubo fallos nuevos. Django no informó incidencias en sus comprobaciones.
No se accedió a Supabase, no se ejecutaron migraciones en esta corrección y no se
usaron los registros reales 30 ni 76. No hubo commits ni push.
La validación local no acredita comportamiento de concurrencia ni paridad con PostgreSQL.

---

## Registro histórico anterior a la corrección

Lo que sigue documenta la ejecución previa. Sus referencias a migraciones, al defecto
pendiente y a comandos de ejecución describen ese momento; para repetir la validación
sin migraciones se deben usar los comandos vigentes indicados arriba.

Fecha: 21 de octubre de 2026. Ejecución local con Django 5.2.6 y DRF.

## 1. Alcance y aislamiento

Se revisaron `api/urls.py`, `api/views.py`, `api/serializers.py`, `api/models.py`,
`api/carga.py`, `api/autenticacion.py` y las pruebas existentes.
Solo se añadieron archivos de pruebas, configuración exclusiva de QA y evidencias.
No se modificó código de producción ni se consultó o escribió en Supabase.
No se usaron el evento real 30 ni la subtarea real 76.

`api.tests.settings_qa` vacía DATABASE_URL antes de cargar la configuración y define
SQLite en memoria tanto para la conexión como para su base de pruebas. Django aplica
las migraciones únicamente allí. APITestCase aísla cada caso mediante transacciones.
Los tokens y organizadores se generan localmente; no se publican credenciales.

## 2. Endpoints y reglas encontradas

Todas las rutas siguientes llevan el prefijo `/api/` y requieren sesión Bearer.
El evento se filtra por organizador; un evento ajeno se responde con 404.

| Ruta | Método | Comportamiento |
| --- | --- | --- |
| `events/{evento}/subtasks/` | GET | Lista por fecha objetivo e ID; HTTP 200. |
| `events/{evento}/subtasks/` | POST | El evento de la URL prevalece sobre el cuerpo; crea con HTTP 201. |
| `events/{evento}/subtasks/{subtarea}/` | PATCH | Actualización parcial; HTTP 200, 400 o 409. |
| Misma ruta de detalle | DELETE | Elimina la subtarea; HTTP 204 sin cuerpo; inexistente: 404. |
| Detalle + `sugerencia-posponer/` | GET | Sugiere fecha sin guardar; HTTP 200; ejecutada: 400. |
| `events/{evento}/progress/` | GET | Ejecutadas / total, porcentaje con un decimal; HTTP 200. |
| `events/{evento}/conflicts/` | GET | Conflictos diarios del evento con carga del organizador; HTTP 200. |

- Estados: PENDIENTE, EJECUTADA y POSPUESTA. La situación se calcula como
  VENCIDA, PARA_HOY, PROXIMA o EJECUTADA y es de solo lectura.
- Marcar ejecutada conserva fecha, horas y nota si no se envían cambios. Una vencida
  puede ejecutarse sin reprogramarla. Las ejecutadas no ocupan carga diaria.
- Posponer admite nota y fecha opcionales. Sin fecha conserva la anterior. Si se envía
  estado POSPUESTA y fecha, esta debe avanzar; una ejecutada no puede posponerse.
  Reprogramar una ya pospuesta sin reenviar estado usa las reglas generales.
- La nota se recorta y los espacios se normalizan a null; omitirla conserva su valor.
- Nombre obligatorio, máximo 200 caracteres; horas positivas, máximo un decimal.
  El serializer no exige múltiplos de 0,5. Las fechas no pueden superar el día del
  evento en America/Bogota; un cambio de fecha no puede ir al pasado.
  La prohibición de pasado se aplica a cambios en PATCH, no a creación.
- La carga suma pendientes y pospuestas de todos los eventos del organizador.
  No cuenta otra cuenta ni duplica la subtarea que se edita.
- Superar el límite diario produce 409 `sobrecarga_diaria`, con cifras y sugerencia,
  sin guardar. Confirmar permite guardar; superar 24 horas produce 400 `dia_excedido`.
  Reducir horas sin cambiar fecha puede aliviar un día superior a 24 horas, pero si
  sigue superando el límite requiere confirmación. Exactamente 24 admite confirmación.

## 3. Pruebas pendientes identificadas y ejecutadas

La suite existente ya tenía ejecución, notas, posposición, sugerencias, progreso,
sobrecarga, confirmación, límites de 24 horas y separación por organizador.
Se añadieron siete pruebas en `api/tests/test_subtareas_qa.py`; una de ellas recorre
11 entradas inválidas con subTest.

| Área | Evidencia automatizada | HTTP verificado | Resultado |
| --- | --- | --- | --- |
| Ejecución | Repetir ejecución conserva fecha, horas y nota | 200 | Conforme |
| Posposición | Fecha posterior, nota opcional, vencida, sugerencia sin escritura | 200 | Conforme, suite existente |
| Posposición inválida | Misma fecha, anterior, posterior al evento o ejecutada | 400 | Conforme, suite existente |
| Sobrecarga | Rechazo sin persistencia y confirmación posterior | 409 / 200; POST 409 / 201 | Conforme, suite existente |
| Capacidad física | Más de 24 h incluso con confirmación | 400 | Conforme, suite existente |
| Validaciones PATCH | Nombre vacío/nulo/largo, horas cero/negativas/texto/nulas/decimales extra, estado y fecha inválidos/pasados | 400 | Conforme; registro completo sin cambios |
| Eliminación propia | Cuerpo vacío, libera carga, reduce total del progreso y conserva otra subtarea | 204 / 200 | Conforme |
| Eliminación repetida | Segunda eliminación de la misma subtarea | 404 | Conforme |
| Eliminación sin sesión | Conserva registro | 401 | Conforme |
| Eliminación ajena o URL con evento incorrecto | Conserva registro | 404 | Conforme |
| Traslado por PATCH a evento ajeno | Debe rechazar y conservar evento original | Esperado 400; observado 200 | Defecto reproducido |

## 4. Defecto QA-01: traslado de subtarea a otra cuenta

Prioridad propuesta: alta, por afectar la separación de datos entre organizadores.

Pasos reproducidos exclusivamente en memoria:

1. Crear organizadores A y B con sus eventos, y una subtarea del evento de A.
2. Autenticarse como A.
3. Enviar PATCH a la URL de la subtarea de A con `{"evento": ID_EVENTO_DE_B}`.
4. Consultar la subtarea mediante ORM en la base de pruebas.

Esperado: rechazar el cambio de propietario indirecto y conservar el evento de A.
La prueba define HTTP 400 como contrato propuesto para ese rechazo.
Observado: HTTP 200 y persistencia del evento de B. La evidencia del fallo muestra
`(200, 2) != (400, 1)`; estos IDs pertenecen únicamente a los objetos locales.

Causa observada: la vista comprueba la propiedad del evento original, pero el campo
`evento` del serializer es escribible y no valida el propietario del destino en PATCH.
Esto permite introducir una subtarea en un evento ajeno; no demuestra por sí solo
lectura de subtareas ajenas. No se corrigió producción. Propuesta para revisión:
impedir reasignación por PATCH o validar explícitamente el destino y su carga.
La prueba queda fallando deliberadamente como regresión pendiente de corrección.

## 5. Resultado y reproducción

```bash
.venv/bin/python manage.py test api.tests --settings=api.tests.settings_qa --verbosity=2
```

Resultado final: **134 pruebas ejecutadas, 133 correctas, 1 fallo**, 13,450 segundos.
Código de salida del proceso: **1**, debido a QA-01; no es un código HTTP.
Comprobaciones de Django: sin incidencias. Base en memoria destruida al finalizar.
De las siete pruebas nuevas, seis pasan y una detecta QA-01.
Evidencia íntegra de la ejecución final: `docs/qa/subtareas_resultados.txt`.

Para ejecutar únicamente los nuevos casos:

```bash
.venv/bin/python manage.py test api.tests.test_subtareas_qa --settings=api.tests.settings_qa --verbosity=2
```

## 6. Pendientes posteriores

- Corregir QA-01 tras autorización para modificar producción y repetir la regresión.
- Acordar si crear fechas pasadas y permitir décimas distintas de media hora son reglas
  deseadas; se documentan como comportamiento actual, no como defectos confirmados.
- Probar concurrencia de escrituras y paridad con PostgreSQL en una base desechable
  autorizada. SQLite no verifica bloqueos, carreras de sobrecarga ni permisos de Supabase.
- Las pruebas HTTP usan el cliente de Django; no verifican proxy, TLS ni despliegue.
  Cualquier prueba que escriba en Supabase requiere confirmación previa y queda pendiente.
