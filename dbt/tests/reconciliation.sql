select * from {{ ref('quality_summary') }}
where raw_rows <> exact_duplicates + rejected_rows + valid_rows
