# Sample Documents Setup

Place your PDF files in this folder and create a matching sidecar `.json` file for each PDF.

## File naming rule

For every PDF:

- `my-policy.pdf`
- `my-policy.json`

## Sidecar format

Each sidecar file must contain `allowed_roles`:

```json
{
  "allowed_roles": ["HR_Manager", "Admin"]
}
```

## Included templates

- `salary-policy.json` (HR/Admin)
- `intern-handbook.json` (Intern/HR/Admin)
- `admin-runbook.json` (Admin only)

## Ingestion command

Run from the repository root:

```powershell
python ingestion/ingest_pdfs.py --input-dir ./documents --default-roles Intern
```

Notes:

- If a PDF has a sidecar `.json`, that `allowed_roles` list is used.
- If a PDF has no sidecar `.json`, the `--default-roles` fallback is used.
- If roles resolve to an empty list, ingestion denies that document by default.
