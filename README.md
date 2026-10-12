
## Architektūra

```mermaid
flowchart LR
    U["Web browser"]
    A["Public API client"]

    subgraph R["Render Web Service"]
        subgraph APP["Python application"]
            W["Flask<br/>Web pages and CRUD API"]
            B["Background thread<br/>Checks incubation dates<br/>every ~30 seconds"]
        end
    end

    D[("Supabase PostgreSQL<br/>Sample records")]
    S["Supabase Storage<br/>Sample photos"]

    U -->|"HTTP(S)"| W
    A -->|"HTTP(S) / JSON"| W
    W -->|"SQLAlchemy"| D
    W -->|"S3 API"| S
    B -->|"Updates incubation status"| D
```

## Public API

- `GET /api/samples` – sample list.
- `GET /api/samples/<id>` – one sample.
- `POST /api/samples` – create sample.
- `PUT /api/samples/<id>` – update sample.
- `DELETE /api/samples/<id>` – delete sample.

POST ir PUT JSON pavyzdys:

```json
{
  "name": "API demonstracija A",
  "colony_count": 12,
  "temperature": 25.5,
  "is_pathogenic": false,
  "incubation_started_on": "2026-10-05",
  "incubation_ends_on": "2026-10-20",
  "incubation_status": "Incubating"
}
```

curl -i -X POST 'https://petri-log.onrender.com/api/samples' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "API demonstracija A",
    "colony_count": 12,
    "temperature": 25.5,
    "is_pathogenic": false,
    "incubation_started_on": "2026-10-05",
    "incubation_ends_on": "2026-10-20",
    "incubation_status": "Incubating"
  }'

curl -i -X PUT 'https://petri-log.onrender.com/api/samples/xxxxx' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "API demonstracija A",
    "colony_count": 12,
    "temperature": 25.5,
    "is_pathogenic": true,
    "incubation_started_on": "2026-10-05",
    "incubation_ends_on": "2026-10-20",
    "incubation_status": "Incubating"
  }'
