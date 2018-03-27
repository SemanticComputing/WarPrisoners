# WarSampo Prisoners of war data conversion

Convert the Prisoners of War dataset from Excel files to enriched RDF.

## Conversion

Requires Docker and Docker Compose.

Create directories `./data/` and `./output/`.
The initial Excel files (`prisoners.xls`, `hospitals.xlsx`, and `camps.xlsx`) should be placed in `./data/`.

Build the conversion pipeline:

`docker-compose build`

Start the required services:

`docker-compose up -d las arpa fuseki`

Run the conversion process:

`docker-compose run --rm tasks`

The output files will be written to `./output/`, and logs to `./output/logs/`.

## Tests

To run all tests: `nosetests --doctest-tests`
