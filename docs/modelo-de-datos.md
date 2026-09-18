# Modelo de datos

Organizador de Eventos Independientes. Grupo 2, Proyecto Integrador I.

**Estado: propuesta.** Cuatro decisiones siguen abiertas y están listadas al final. El diagrama
refleja la opción recomendada en cada una. Si el equipo decide distinto, este archivo se corrige por
pull request antes de escribir los modelos de Django.

## Diagrama entidad relación

```mermaid
erDiagram
    ORGANIZADOR ||--o{ EVENTO : "organiza"
    EVENTO ||--o{ SUBTAREA_LOGISTICA : "se descompone en"

    ORGANIZADOR {
        int id PK
        string nombre
        string identidad_externa "Sprint 2, id del proveedor de autenticacion"
        decimal limite_diario_horas "US-12, default 6, rango 1 a 16"
        datetime creado_en
    }

    EVENTO {
        int id PK
        int organizador_id FK "US-11, aislamiento por usuario"
        string nombre "US-01"
        string tipo "US-01, boda social corporativo cumpleanos otro"
        string cliente_contacto "US-01, texto libre"
        datetime fecha_hora_evento "US-01"
        string lugar "US-01, pendiente de confirmar con el docente"
        date plazo_limite "US-01, pendiente de confirmar con el docente"
        datetime creado_en
        datetime actualizado_en
    }

    SUBTAREA_LOGISTICA {
        int id PK
        int evento_id FK "US-02, on delete CASCADE"
        string nombre "US-02, nombre de la gestion"
        date fecha_objetivo "US-02 y US-06"
        decimal horas_estimadas "US-02, mayor que 0, paso 0.5"
        string estado "US-09, PENDIENTE EJECUTADA POSPUESTA"
        text nota_posposicion "US-09, opcional"
        datetime creado_en
        datetime actualizado_en
    }
```

## Regla de trazabilidad

Cada campo tiene anotada la historia de usuario que lo exige. Un campo sin historia detrás no entra
al modelo. El enunciado pide centrarse en lo que piden los requerimientos, y cada columna de más es
trabajo de mantenimiento que nadie pidió.

## Lo que no se guarda porque se calcula

Tres datos parecen campos y no lo son. Guardarlos obliga a mantenerlos sincronizados, y cuando se
desincronizan la interfaz miente sin lanzar ningún error.

| Dato | Cómo se obtiene | Historia |
| --- | --- | --- |
| Vencida, Para hoy o Próxima | Comparar `fecha_objetivo` con la fecha de hoy, excluyendo lo EJECUTADO | US-04 |
| Progreso del evento | Subtareas EJECUTADA sobre el total de subtareas del evento | US-10 |
| Horas planificadas de un día | Suma de `horas_estimadas` de las subtareas con esa `fecha_objetivo` y estado distinto de EJECUTADA | US-07 |

## Campos omitidos a propósito

**`email` y `password_hash`.** Las credenciales las administra un proveedor externo, Supabase Auth
por defecto y Firebase Auth solo si el docente lo exige. La aplicación no es dueña de las
contraseñas, así que no las modela. En el Sprint 2 se agrega `identidad_externa` con el
identificador del usuario en el proveedor que quede elegido.

**Descripción de la subtarea.** US-02 lista los campos mínimos: nombre, plazo y horas estimadas.

**Fecha de ejecución.** US-09 pide guardar el estado, no cuándo cambió.

**Estado del evento.** Ninguna historia lo pide. El progreso se deriva de las subtareas.

## Decisiones abiertas

1. Límite diario: ¿atributo del organizador o entidad propia? El diagrama usa atributo. TS-02
   menciona "configuración de límite diario" entre las entidades, y esa redacción admite las dos
   lecturas.
2. Borrado de evento: ¿cascada o borrado lógico? El diagrama usa cascada.
3. Horas estimadas: ¿enteros o decimales de media hora? El diagrama usa decimales, porque US-08
   permite reducir horas para resolver un conflicto y con enteros una gestión de una hora solo
   podría bajar a cero, que US-02 prohíbe.
4. ¿Una gestión POSPUESTA sigue contando en las horas planificadas de su día? Lectura propuesta: sí,
   porque conserva fecha objetivo. Solo se excluye lo EJECUTADO.

Pendientes de aclarar con el docente: si "lugar/plazo límite" en US-01 son uno o dos campos, y si el
plazo límite es distinto de la fecha del evento.
